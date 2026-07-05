import os
import time
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Form, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.rate_limiter import check_rate_limit
from app import analytics
from app.agents.codegen import generate_code
from app.agents.review import review_code
from app.agents.debug import debug_code
from app.llm_client import GroqClientError, DEFAULT_MODEL
from app import rag

load_dotenv()

app = FastAPI(title="AI Dev Mentor API", version="1.0.0")

allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c"}
MAX_FILE_SIZE_BYTES = 200 * 1024  # 200KB


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1)
    model: Optional[str] = None


class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1)
    model: Optional[str] = None
    session_id: Optional[str] = None


class DebugRequest(BaseModel):
    code: str = Field(..., min_length=1)
    error: str = Field(..., min_length=1)
    language: str = Field(..., min_length=1)
    model: Optional[str] = None


class AgentResult(BaseModel):
    result: str


class RagUploadResult(BaseModel):
    session_id: str
    files_processed: int
    chunks_stored: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _timed(endpoint: str, request: Request, fn, *args, **kwargs):
    check_rate_limit(request)
    start = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event(endpoint, elapsed_ms, success=True)
        return result
    except GroqClientError as e:
        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event(endpoint, elapsed_ms, success=False)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event(endpoint, elapsed_ms, success=False)
        raise
    except Exception:
        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event(endpoint, elapsed_ms, success=False)
        raise HTTPException(status_code=500, detail="Internal server error.")


# ---------------------------------------------------------------------------
# Health & root
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def welcome():
    return {"message": "Welcome to the AI Dev Mentor API. See /health for status."}


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------

@app.post("/agent/generate", response_model=AgentResult)
async def agent_generate(payload: GenerateRequest, request: Request):
    model = payload.model or DEFAULT_MODEL
    result = await _timed(
        "/agent/generate", request, generate_code, payload.prompt, payload.language, model
    )
    return {"result": result}


@app.post("/agent/review", response_model=AgentResult)
async def agent_review(payload: ReviewRequest, request: Request):
    model = payload.model or DEFAULT_MODEL
    retrieved_context = None

    if payload.session_id:
        try:
            chunks = rag.retrieve_relevant_chunks(payload.session_id, payload.code, top_k=4)
            if chunks:
                retrieved_context = "\n\n".join(c["text"] for c in chunks)
        except Exception:
            # RAG retrieval failing should not block a plain review
            retrieved_context = None

    result = await _timed(
        "/agent/review",
        request,
        review_code,
        payload.code,
        payload.language,
        model,
        retrieved_context,
    )
    return {"result": result}


@app.post("/agent/debug", response_model=AgentResult)
async def agent_debug(payload: DebugRequest, request: Request):
    model = payload.model or DEFAULT_MODEL
    result = await _timed(
        "/agent/debug", request, debug_code, payload.code, payload.error, payload.language, model
    )
    return {"result": result}


# ---------------------------------------------------------------------------
# RAG upload endpoint
# ---------------------------------------------------------------------------

@app.post("/rag/upload", response_model=RagUploadResult)
async def rag_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
):
    check_rate_limit(request)
    start = time.time()

    session = session_id or str(uuid.uuid4())
    files_processed = 0
    chunks_stored = 0

    try:
        for f in files:
            filename = f.filename or ""
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type '{ext or 'unknown'}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )

            content_bytes = await f.read()
            if len(content_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{filename}' exceeds the 200KB size limit.",
                )

            try:
                content_text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail=f"File '{filename}' is not valid UTF-8 text.")

            chunks = rag.chunk_code(content_text, filename)
            stored = rag.embed_and_store(session, chunks)
            chunks_stored += stored
            files_processed += 1

        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event("/rag/upload", elapsed_ms, success=True)
        return {
            "session_id": session,
            "files_processed": files_processed,
            "chunks_stored": chunks_stored,
        }
    except HTTPException:
        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event("/rag/upload", elapsed_ms, success=False)
        raise
    except Exception:
        elapsed_ms = (time.time() - start) * 1000
        analytics.log_event("/rag/upload", elapsed_ms, success=False)
        raise HTTPException(status_code=502, detail="Failed to process uploaded files.")


# ---------------------------------------------------------------------------
# Admin endpoint
# ---------------------------------------------------------------------------

@app.get("/admin/stats")
def admin_stats(x_admin_secret: Optional[str] = Header(None)):
    expected = os.environ.get("ADMIN_SECRET")
    if not expected or x_admin_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin secret.")
    return analytics.get_stats()
