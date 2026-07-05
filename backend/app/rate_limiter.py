"""
Simple in-memory sliding-window rate limiter: 50 requests per hour per client IP.

NOTE: This state lives in process memory only and resets on every restart/deploy.
That's an accepted tradeoff for this project's scope — a production system would
back this with Redis or similar shared storage.
"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, HTTPException

WINDOW_SECONDS = 60 * 60
MAX_REQUESTS_PER_WINDOW = 50

_lock = Lock()
_request_log: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _prune(ip: str, now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    _request_log[ip] = [t for t in _request_log[ip] if t > cutoff]


def check_rate_limit(request: Request) -> None:
    ip = get_client_ip(request)
    now = time.time()
    with _lock:
        _prune(ip, now)
        if len(_request_log[ip]) >= MAX_REQUESTS_PER_WINDOW:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded: max 50 requests per hour per client. Please try again later.",
            )
        _request_log[ip].append(now)
