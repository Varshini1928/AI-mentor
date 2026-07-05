"""
In-memory analytics event log for request metrics + admin dashboard stats.

Like the rate limiter, this state resets on restart. Fine for a project of this
scope; a production version would persist events to a database.
"""
import time
from collections import defaultdict
from threading import Lock
from typing import List

_lock = Lock()
_events: List[dict] = []


def log_event(endpoint: str, response_time_ms: float, success: bool) -> None:
    with _lock:
        _events.append(
            {
                "timestamp": time.time(),
                "endpoint": endpoint,
                "response_time_ms": response_time_ms,
                "success": success,
            }
        )


def get_stats() -> dict:
    with _lock:
        events = list(_events)

    total_queries = len(events)
    queries_by_endpoint: dict[str, int] = defaultdict(int)
    total_response_time = 0.0
    error_count = 0
    now = time.time()
    queries_last_hour = 0

    for event in events:
        queries_by_endpoint[event["endpoint"]] += 1
        total_response_time += event["response_time_ms"]
        if not event["success"]:
            error_count += 1
        if now - event["timestamp"] <= 3600:
            queries_last_hour += 1

    average_response_time_ms = (total_response_time / total_queries) if total_queries else 0.0
    error_rate_percent = (error_count / total_queries * 100) if total_queries else 0.0

    return {
        "total_queries": total_queries,
        "queries_by_endpoint": dict(queries_by_endpoint),
        "average_response_time_ms": round(average_response_time_ms, 2),
        "error_rate_percent": round(error_rate_percent, 2),
        "queries_last_hour": queries_last_hour,
    }
