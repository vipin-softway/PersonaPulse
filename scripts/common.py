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
