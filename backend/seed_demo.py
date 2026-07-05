"""
Heuristic RAG pipeline for grounding code review in the user's own project.

Chunking is intentionally heuristic (regex-based splitting), not full AST parsing.
This is a deliberate scope decision — good enough to retrieve relevant functions/
classes for review context without the complexity of a real parser per language.
"""
import os
import re
import time
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "code_chunks"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension
CHUNK_TOKEN_APPROX_CHARS = 500 * 4  # ~500 tokens, rough chars-per-token heuristic
OVERLAP_APPROX_CHARS = 50 * 4

_client: Optional[QdrantClient] = None
_embedder: Optional[SentenceTransformer] = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        url = os.environ.get("QDRANT_URL")
        api_key = os.environ.get("QDRANT_API_KEY")
        # Free-tier Qdrant Cloud clusters can be slow to respond, especially
        # right after being idle/"cold". The client's default timeout (a few
        # seconds) is too short for that, so we raise it here.
        _client = QdrantClient(url=url, api_key=api_key, timeout=60)
        _ensure_collection(_client)
    return _client


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_PY_SPLIT_RE = re.compile(r"^(?=(?:def |class )\S)", re.MULTILINE)
_JS_SPLIT_RE = re.compile(
    r"^(?=(?:function\s|const\s+\w+\s*=|class\s|export\s+function\s|export\s+const\s))",
    re.MULTILINE,
)


def _fallback_chunks(content: str) -> List[str]:
    chunks = []
    step = CHUNK_TOKEN_APPROX_CHARS - OVERLAP_APPROX_CHARS
    for start in range(0, len(content), step):
        chunk = content[start : start + CHUNK_TOKEN_APPROX_CHARS]
        if chunk.strip():
            chunks.append(chunk)
        if start + CHUNK_TOKEN_APPROX_CHARS >= len(content):
            break
    return chunks or [content]


def chunk_code(file_content: str, filename: str) -> List[dict]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "py":
        pieces = _PY_SPLIT_RE.split(file_content)
        pieces = [p for p in pieces if p.strip()]
        if not pieces:
            pieces = _fallback_chunks(file_content)
    elif ext in ("js", "ts", "jsx", "tsx"):
        pieces = _JS_SPLIT_RE.split(file_content)
        pieces = [p for p in pieces if p.strip()]
        if not pieces:
            pieces = _fallback_chunks(file_content)
    else:
        pieces = _fallback_chunks(file_content)

    return [
        {"filename": filename, "chunk_index": i, "text": piece.strip()}
        for i, piece in enumerate(pieces)
        if piece.strip()
    ]


# ---------------------------------------------------------------------------
# Embedding + storage
# ---------------------------------------------------------------------------

def embed_and_store(session_id: str, chunks: List[dict]) -> int:
    if not chunks:
        return 0
    client = get_client()
    embedder = get_embedder()

    texts = [c["text"] for c in chunks]
    vectors = embedder.encode(texts).tolist()

    points = [
        qmodels.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "session_id": session_id,
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
            },
        )
        for vector, chunk in zip(vectors, chunks)
    ]

    last_error = None
    for attempt in range(3):
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            return len(points)
        except Exception as e:  # covers ResponseHandlingException/timeouts
            last_error = e
            time.sleep(2 * (attempt + 1))  # brief backoff, gives a slow/cold cluster time to respond
    raise last_error


def retrieve_relevant_chunks(session_id: str, query: str, top_k: int = 4) -> List[dict]:
    client = get_client()
    embedder = get_embedder()
    query_vector = embedder.encode([query])[0].tolist()

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(key="session_id", match=qmodels.MatchValue(value=session_id))]
        ),
        limit=top_k,
    )
    return [
        {
            "filename": r.payload.get("filename"),
            "chunk_index": r.payload.get("chunk_index"),
            "text": r.payload.get("text"),
            "score": r.score,
        }
        for r in results
    ]