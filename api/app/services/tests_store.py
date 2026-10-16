"""Save and load tests: one `tests` row per variant, one `simulation_results` row per persona.

Recent results are also kept in memory so the results page loads instantly
right after a test, and still works if a BigQuery write is delayed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigquery

from app.services import bq
from app.services.aggregate import aggregate_variant, build_test_result

log = logging.getLogger("personapulse.store")

_RECENT: OrderedDict[str, dict] = OrderedDict()
_RECENT_MAX = 200


def remember(result: dict) -> None:
    _RECENT[result["test_id"]] = result
    _RECENT.move_to_end(result["test_id"])
    while len(_RECENT) > _RECENT_MAX:
        _RECENT.popitem(last=False)


def recent(test_id: str) -> dict | None:
    return _RECENT.get(test_id)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def with_display(rows: list[dict], personas: list[dict]) -> list[dict]:
    """Join persona display fields (name, age, city, segment) onto reaction rows for the dashboard."""
    by_id = {p["persona_id"]: p for p in personas}
    out = []
    for r in rows:
        p = by_id.get(r["persona_id"], {})
        out.append({**r, "persona_name": p.get("name"), "age": p.get("age"), "city": p.get("city"),
                    "segment_name": p.get("segment_name")})
    return out


async def save_variant(*, test_id: str, variant: str, panel: str, product: dict, rows: list[dict], run: dict,
                       image_uri: str | None, ip_hash: str | None, themes: dict | None = None,
                       parent_variant: str | None = None) -> None:
    """Write to BigQuery. Failures are logged, not raised: the user still gets their result."""
    created = run.get("run_at") or now_iso()
    try:
        await asyncio.gather(
            bq.insert("tests", [{
                "test_id": test_id, "variant": variant, "panel": panel, "product": product,
                "parent_variant": parent_variant, "status": "complete", "n_personas": len(rows), "is_demo": False,
                "client_ip_hash": ip_hash, "created_at": created, "run": run, "image_uri": image_uri,
            }], json_fields=("product", "run")),
            bq.insert("simulation_results", [{**r, "test_id": test_id, "variant": variant, "created_at": created}
                                             for r in rows]),
            bq.insert("insights", [{"test_id": test_id, "variant": variant, "kind": "themes", "payload": themes,
                                    "model": "text-embedding-005", "created_at": created}] if themes else [],
                      json_fields=("payload",)),
        )
    except Exception:  # noqa: BLE001
        log.exception("Saving test %s/%s to BigQuery failed", test_id, variant)


async def save_insight(test_id: str, variant: str | None, kind: str, payload: Any, model: str) -> None:
    try:
        await bq.insert("insights", [{"test_id": test_id, "variant": variant, "kind": kind, "payload": payload,
                                      "model": model, "created_at": now_iso()}], json_fields=("payload",))
    except Exception:  # noqa: BLE001
        log.exception("Saving %s insight for %s failed", kind, test_id)


async def image_uri(test_id: str, variant: str) -> str | None:
    rows = await bq.query(
        f"SELECT image_uri FROM {bq.table('tests')} WHERE test_id = @id AND variant = @v AND image_uri IS NOT NULL LIMIT 1",
        [bigquery.ScalarQueryParameter("id", "STRING", test_id), bigquery.ScalarQueryParameter("v", "STRING", variant)])
    return rows[0]["image_uri"] if rows else None


def _json(v: Any) -> Any:
    return json.loads(v) if isinstance(v, str) else v


async def load_test(test_id: str) -> dict | None:
    """Rebuild a test result from BigQuery, or None if it doesn't exist."""
    param = [bigquery.ScalarQueryParameter("id", "STRING", test_id)]
    tests = await bq.query(
        f"SELECT variant, panel, product, run, image_uri, created_at FROM {bq.table('tests')} "
        f"WHERE test_id = @id ORDER BY created_at", param)
    if not tests:
        return None
    panel = tests[0]["panel"]
    results, segments, insights = await asyncio.gather(
        bq.query(
            f"""SELECT r.*, p.name AS persona_name, p.age, p.city, p.segment_name
                FROM {bq.table('simulation_results')} r
                LEFT JOIN {bq.table('personas')} p USING (persona_id)
                WHERE r.test_id = @id""", param),
        bq.query(f"SELECT segment_id, name, share FROM {bq.table('segments')} WHERE panel = @panel ORDER BY share DESC",
                 [bigquery.ScalarQueryParameter("panel", "STRING", panel)]),
        bq.query(f"SELECT variant, kind, payload FROM {bq.table('insights')} WHERE test_id = @id ORDER BY created_at",
                 param),
    )
    summaries = {i["variant"]: _json(i["payload"]) for i in insights if i["kind"] == "summary"}
    themes = {i["variant"]: _json(i["payload"]) for i in insights if i["kind"] == "themes"}
    suggestions = next((_json(i["payload"]) for i in reversed(insights) if i["kind"] == "suggestions"), [])

    variants = []
    for t in tests:
        rows = [dict(r) for r in results if r["variant"] == t["variant"]]
        product = _json(t["product"]) or {}
        v = aggregate_variant(t["variant"], product, rows, segments, themes.get(t["variant"]))
        v["insights"] = summaries.get(t["variant"])
        variants.append(v)
    first = tests[0]
    run = _json(first["run"]) or None
    return build_test_result(test_id, variants, created_at=first["created_at"].isoformat(), panel=panel,
                             suggestions=suggestions, run=run)
