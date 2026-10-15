"""Bundled JSON results that load without BigQuery or Gemini (hard rule 3)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parents[1] / "data"


@lru_cache
def load(name: str) -> dict:
    return json.loads((_DATA / name).read_text(encoding="utf-8"))
