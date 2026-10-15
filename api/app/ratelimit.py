"""Simple in-memory per-IP rate limit for POST endpoints.

Per Cloud Run instance, which is fine for a hackathon: it stops a single
visitor from hammering Gemini. Use as `dependencies=[Depends(rate_limit)]`.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings

_WINDOW_S = 60
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Cloud Run sets X-Forwarded-For; the first entry is the original client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    limit = get_settings().rate_limit_per_min
    now = time.monotonic()
    q = _hits[_client_ip(request)]
    while q and now - q[0] > _WINDOW_S:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            status_code=429,
            detail="You're running tests quickly. Please wait a minute and try again.",
        )
    q.append(now)
