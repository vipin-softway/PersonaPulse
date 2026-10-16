"""Runtime configuration, read once from environment variables.

No secrets live here: Vertex AI and BigQuery authenticate with Application
Default Credentials (the Cloud Run service account in production,
`gcloud auth application-default login` locally).
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    gcp_project: str = field(default_factory=lambda: os.getenv("GCP_PROJECT", ""))
    # Gemini endpoint location. "global" serves the newest models; BigQuery keeps its own (US) location.
    gcp_location: str = field(default_factory=lambda: os.getenv("GCP_LOCATION", "global"))
    bq_dataset: str = field(default_factory=lambda: os.getenv("BQ_DATASET", "personapulse"))
    gcs_bucket: str = field(default_factory=lambda: os.getenv("GCS_BUCKET", ""))  # product images; empty = off
    gemini_flash_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_FLASH_MODEL", "gemini-3.8-flash")
    )
    gemini_pro_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_PRO_MODEL", "gemini-3.1-pro-preview")
    )
    # Used if the Pro model is rate-limited or unavailable (preview models can be).
    gemini_pro_fallback_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_PRO_FALLBACK_MODEL", "gemini-2.5-pro")
    )
    allowed_origins: list[str] = field(
        default_factory=lambda: _list("ALLOWED_ORIGINS", "http://localhost:3000")
    )
    max_live_personas: int = field(default_factory=lambda: _int("MAX_LIVE_PERSONAS", 30))
    gemini_concurrency: int = field(default_factory=lambda: _int("GEMINI_CONCURRENCY", 30))
    gemini_timeout_s: int = field(default_factory=lambda: _int("GEMINI_TIMEOUT_S", 45))
    rate_limit_per_min: int = field(default_factory=lambda: _int("RATE_LIMIT_PER_MIN", 8))
    # Live runs (tests, suggestions, retests) per instance per day; protects the budget.
    max_tests_per_day: int = field(default_factory=lambda: _int("MAX_TESTS_PER_DAY", 300))


@lru_cache
def get_settings() -> Settings:
    return Settings()
