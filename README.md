# AI Dev Mentor

An AI-powered coding assistant that generates code, reviews it, and helps debug errors —
with review quality boosted by a lightweight RAG pipeline grounded in your own uploaded
project files.

## Problem Statement

Developers, especially those learning or working solo, often lack a fast, always-available
mentor to sanity-check generated code, review pull-request-sized snippets, or walk through
a stack trace. Generic chatbots can help, but they don't ground their reviews in the
conventions already used elsewhere in a developer's own codebase. AI Dev Mentor addresses
this by combining three focused agents (generate / review / debug) with a retrieval step
that pulls in relevant code the user has already uploaded, so review feedback can reference
real project context instead of judging a snippet in isolation.

## Tech Stack

| Layer          | Technology                                                   |
|----------------|---------------------------------------------------------------|
| Backend        | Python, FastAPI, Docker                                       |
| LLM inference  | Groq API (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`)         |
| Vector store   | Qdrant                                                         |
| Embeddings     | `sentence-transformers` (`all-MiniLM-L6-v2`)                   |
| Frontend       | Next.js 15 (App Router), plain JavaScript, Tailwind CSS        |
| Backend deploy | Render (Docker web service)                                    |
| Frontend deploy| Vercel                                                          |

> **Model note:** The original brief specified `llama-3.3-70b-versatile` and
> `mixtral-8x7b-32768`. Both are deprecated on Groq as of mid-2026, so this build uses
> Groq's current recommended replacements, `openai/gpt-oss-120b` and `openai/gpt-oss-20b`.
> Always re-check https://console.groq.com/docs/models before relying on hardcoded IDs.

## Architecture Overview

```
┌─────────────┐        HTTPS         ┌──────────────────┐        HTTPS        ┌───────────┐
│  Next.js UI │ ───────────────────► │  FastAPI backend │ ──────────────────► │ Groq API  │
│  (Vercel)   │ ◄─────────────────── │    (Render)       │ ◄────────────────── │ (LLM)     │
└─────────────┘      JSON results     └──────────────────┘     completion       └───────────┘
                                              │  ▲
                                   embed/search│  │ retrieved chunks
                                              ▼  │
                                        ┌──────────────┐
                                        │   Qdrant      │
                                        │ (code_chunks) │
                                        └──────────────┘
```

Request flow for a grounded review:
1. User uploads project files (or clicks "Try RAG Example") → backend chunks the code
   heuristically (by function/class boundaries, or fixed-size fallback) and stores
   embeddings in Qdrant under a `session_id`.
2. User submits code to review → backend embeds the query, retrieves the top-k most
   similar chunks for that `session_id`, and prepends them as context to the review prompt.
3. The review agent calls Groq with the augmented prompt and returns structured markdown
   feedback, rendered in the UI.
4. Every request passes through an in-memory rate limiter (50/hr per IP) and is logged
   for the analytics dashboard.

## Features

| Feature                                   | Course Requirement          |
|--------------------------------------------|------------------------------|
| Code generation agent                      | Core agent #1                |
| Code review agent (with few-shot prompting)| Core agent #2                |
| Debugging agent (chain-of-thought)         | Core agent #3                |
| RAG pipeline over uploaded code             | Context-aware / grounded AI  |
| Rate limiting (50 req/hr/IP)                | Production hardening         |
| Analytics + admin dashboard                 | Observability                |
| Multi-LLM toggle                            | Optional / stretch           |
| Voice input (browser SpeechRecognition)     | Optional / stretch           |
| Dockerized backend, Render + Vercel deploy  | Deployment                   |

## Local Setup

### Backend
```bash
cd backend
cp .env.example .env        # fill in GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY, ADMIN_SECRET
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then seed the RAG demo data (requires Qdrant reachable, e.g. Qdrant Cloud free tier):
```bash
python seed_demo.py
```

Or run everything in Docker:
```bash
docker build -t ai-dev-mentor-backend .
docker run --env-file .env -p 8000:8000 ai-dev-mentor-backend
```

### Frontend
```bash
cd frontend
cp .env.local.example .env.local   # points at your local backend by default
npm install
npm run dev
```
Visit `http://localhost:3000`.

## Live URLs

- Frontend: _fill in after deploying to Vercel_
- Backend: _fill in after deploying to Render_

## Known Limitations

- Rate limiting and analytics are in-memory only — both reset on every backend restart
  or redeploy. A production version would use Redis/a database instead.
- RAG chunking is heuristic (regex-based), not full AST parsing, so very unusual code
  formatting may chunk imperfectly.
- The in-memory rate limiter is per-process; if Render scales the backend to multiple
  instances, the effective limit becomes per-instance rather than global.
- Voice input relies on the browser's `SpeechRecognition` API, which has inconsistent
  support outside Chrome-based browsers.

## AI Tools Used

This project was scaffolded and implemented with Claude (Anthropic), based on a detailed
build specification covering backend architecture, prompt design, RAG pipeline, and
frontend UI. Claude also verified current Groq model availability before hardcoding
model IDs, since the originally-specified models had since been deprecated.
