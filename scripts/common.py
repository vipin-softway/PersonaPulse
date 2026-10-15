"""Shared setup for the one-time scripts: env vars from the repo-root .env, BigQuery client."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
BQ_DATASET = os.environ.get("BQ_DATASET", "personapulse")
BQ_LOCATION = os.environ.get("BQ_LOCATION", "US")


def require_project() -> str:
    if not GCP_PROJECT or GCP_PROJECT == "your-project-id":
        raise SystemExit("Set GCP_PROJECT in .env (copy .env.example to .env).")
    return GCP_PROJECT


def bq_client():
    from google.cloud import bigquery

    return bigquery.Client(project=require_project())


def table_id(name: str) -> str:
    return f"{require_project()}.{BQ_DATASET}.{name}"


# --- Gemini (reuses the API's guarded client: timeout, one retry on bad JSON, concurrency cap) ---

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "api"))

PROCESSED = ROOT / "data" / "processed"


async def call_prompt(name: str, *, fallback=None, timeout_s: int = 120, **variables):
    """Render prompt `name` (e.g. "p01_signals") and call Gemini with its configured model and temperature.

    Returns (data, ok). Never raises on model errors; check `ok`.
    """
    from app.config import get_settings
    from app.prompts import CONFIG, render
    from app.services.gemini import generate_json

    kind, temperature = CONFIG[name]
    s = get_settings()
    system, user = render(name, **variables)
    model = s.gemini_pro_model if kind == "pro" else s.gemini_flash_model
    return await generate_json(system=system, user=user, fallback=fallback, model=model,
                               temperature=temperature, timeout_s=timeout_s)


def preview_prompt(name: str, **variables) -> str:
    """Rendered prompt text for --dry-run output."""
    from app.prompts import render

    system, user = render(name, **variables)
    return f"=== SYSTEM ===\n{system}\n=== USER ===\n{user}"


def load_json_to_bq(table: str, rows: list[dict]) -> None:
    """Replace a table's contents with `rows` (batch load: free, and no streaming-buffer limits).

    Uses the table's existing schema (from create_tables.py) so nothing is auto-detected.
    JSON columns take plain dicts/lists.
    """
    from google.cloud import bigquery

    client = bq_client()
    schema = client.get_table(table_id(table)).schema
    job = client.load_table_from_json(
        rows,
        table_id(table),
        job_config=bigquery.LoadJobConfig(schema=schema, autodetect=False, write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    print(f"Loaded {job.output_rows} rows into {table_id(table)}")
