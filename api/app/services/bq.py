"""BigQuery access. Uses Application Default Credentials; no keys.

The client is synchronous, so query helpers run in a worker thread to keep
FastAPI's event loop free.
"""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from typing import Any

from google.cloud import bigquery

from app.config import get_settings


@lru_cache
def client() -> bigquery.Client:
    return bigquery.Client(project=get_settings().gcp_project or None)


def table(name: str) -> str:
    s = get_settings()
    return f"`{s.gcp_project}.{s.bq_dataset}.{name}`"


def _query(sql: str, params: list[bigquery.ScalarQueryParameter] | None) -> list[dict[str, Any]]:
    job = client().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params or []))
    return [dict(row) for row in job.result(timeout=30)]


async def query(
    sql: str, params: list[bigquery.ScalarQueryParameter] | None = None
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_query, sql, params)


def _insert(table_name: str, rows: list[dict[str, Any]], json_fields: tuple[str, ...]) -> None:
    s = get_settings()
    # The streaming API takes JSON columns as JSON strings, not nested objects.
    rows = [{k: (json.dumps(v, ensure_ascii=False) if k in json_fields and v is not None else v) for k, v in r.items()}
            for r in rows]
    errors = client().insert_rows_json(f"{s.gcp_project}.{s.bq_dataset}.{table_name}", rows)
    if errors:
        raise RuntimeError(f"BigQuery insert into {table_name} failed: {errors[:3]}")


async def insert(table_name: str, rows: list[dict[str, Any]], json_fields: tuple[str, ...] = ()) -> None:
    if rows:
        await asyncio.to_thread(_insert, table_name, rows, json_fields)
