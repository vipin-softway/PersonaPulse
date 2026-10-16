"""Per-IP rate limit and a daily cap on live runs, for every POST endpoint.

In-memory per Cloud Run instance (max 3), which is enough for a hackathon:
it stops one visitor hammering Gemini and caps total spend per day.
Use as `dependencies=[Depends(rate_limit)]`.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import date

from fastapi import HTTPException, Request

from app.config import get_settings

_WINDOW_S = 60
_hits: dict[str, deque[float]] = defaultdict(deque)
_day = {"date": date.today(), "count": 0}
_last_prune = time.monotonic()


def _client_ip(request: Request) -> str:
    # Cloud Run sets X-Forwarded-For; the first entry is the original client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(now: float) -> None:
    global _last_prune
    if now - _last_prune < _WINDOW_S:
        return
    for ip in [ip for ip, q in _hits.items() if not q or now - q[-1] > _WINDOW_S]:
        del _hits[ip]
    _last_prune = now


async def rate_limit(request: Request) -> None:
    s = get_settings()
    now = time.monotonic()
    _prune(now)

    today = date.today()
    if _day["date"] != today:
        _day.update(date=today, count=0)
    if _day["count"] >= s.max_tests_per_day:
        raise HTTPException(
            status_code=429,
            detail="Today's live tests are used up. Please explore the demo test, or come back tomorrow.",
        )

    q = _hits[_client_ip(request)]
    while q and now - q[0] > _WINDOW_S:
        q.popleft()
    if len(q) >= s.rate_limit_per_min:
        raise HTTPException(
            status_code=429,
            detail="You're running tests quickly. Please wait a minute and try again.",
        )
    q.append(now)
    _day["count"] += 1
