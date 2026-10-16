"""Live personas and segment shares per panel, read from BigQuery and cached in memory.

The panel only changes when scripts/build_personas.py runs, so a 10-minute
cache keeps live tests fast without serving stale data for long.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.config import get_settings
from app.services import bq

_TTL_S = 600
_cache: dict[str, tuple[float, list[dict], list[dict]]] = {}
_lock = asyncio.Lock()

# Bookkeeping fields that should not be shown to the model in Prompt 4/8.
_INTERNAL = {"memories_claimed", "is_live", "original_preferred_language", "original_name"}


def _profile(raw: Any) -> dict:
    return json.loads(raw) if isinstance(raw, str) else dict(raw or {})


async def load_panel(panel: str) -> tuple[list[dict], list[dict]]:
    """Returns (live personas, segments) for a panel. Raises on BigQuery failure."""
    now = time.monotonic()
    hit = _cache.get(panel)
    if hit and now - hit[0] < _TTL_S:
        return hit[1], hit[2]
    async with _lock:
        hit = _cache.get(panel)
        if hit and time.monotonic() - hit[0] < _TTL_S:
            return hit[1], hit[2]
        p = bq.table("personas")
        sg = bq.table("segments")
        from google.cloud import bigquery

        param = [bigquery.ScalarQueryParameter("panel", "STRING", panel)]
        persona_rows, segment_rows = await asyncio.gather(
            bq.query(f"SELECT persona_id, segment_id, segment_name, name, age, city, profile FROM {p} "
                     f"WHERE panel = @panel AND is_live ORDER BY persona_id", param),
            bq.query(f"SELECT segment_id, name, share FROM {sg} WHERE panel = @panel ORDER BY share DESC", param),
        )
        limit = get_settings().max_live_personas
        personas = []
        for r in persona_rows[:limit]:
            prof = {k: v for k, v in _profile(r["profile"]).items() if k not in _INTERNAL}
            personas.append({**{k: r[k] for k in ("persona_id", "segment_id", "segment_name", "name", "age", "city")},
                             "profile": prof})
        segments = [{"segment_id": r["segment_id"], "name": r["name"], "share": r["share"]} for r in segment_rows]
        _cache[panel] = (time.monotonic(), personas, segments)
        return personas, segments
