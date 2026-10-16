"""Prompt 4: every live persona reacts to one product, in parallel.

Each reaction is validated and normalised before it is saved, so a model that
returns a string price or a 0-10 scale can't break the dashboard. Personas
whose call fails are simply left out; the caller decides if enough answered.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from google.genai import types

from app.config import get_settings
from app.prompts import CONFIG, render
from app.services.gemini import generate_json

NOT_STATED = "Not specified"


def _num(v: Any) -> float | None:
    try:
        f = float(str(v).replace("₹", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def _texts(v: Any, limit: int = 5) -> list[str]:
    items = v if isinstance(v, list) else ([v] if isinstance(v, str) else [])
    return [str(x).strip()[:160] for x in items if str(x).strip()][:limit]


def normalise(raw: Any, persona: dict) -> dict | None:
    """Prompt 4 output -> a simulation_results row, or None if unusable."""
    if not isinstance(raw, dict):
        return None
    intent = _num(raw.get("purchase_intent"))
    if intent is None:
        return None
    intent = int(round(min(5, max(1, intent))))
    would = str(raw.get("would_buy", "")).strip().lower()
    if would not in ("yes", "maybe", "no"):
        would = "yes" if intent >= 4 else "maybe" if intent == 3 else "no"
    quote = str(raw.get("quote") or raw.get("first_impression") or "").strip()
    if not quote:
        return None
    return {
        "persona_id": persona["persona_id"],
        "segment_id": persona["segment_id"],
        "purchase_intent": float(intent),
        "would_buy": would,
        "willingness_to_pay_inr": _num(raw.get("willingness_to_pay_inr")),
        "top_likes": _texts(raw.get("top_likes")),
        "top_objections": _texts(raw.get("top_objections")),
        "main_reason": str(raw.get("main_reason") or "").strip()[:300] or None,
        "quote": quote[:500],
        "first_impression": str(raw.get("first_impression") or "").strip()[:300] or None,
        "what_would_change_my_mind": str(raw.get("what_would_change_my_mind") or "").strip()[:300] or None,
    }


def _price_text(price: float) -> str | float:
    return int(price) if float(price).is_integer() else price


CALL_TIMEOUT_S = 20  # per attempt; a stalled call usually succeeds on a fresh retry
TEST_BUDGET_S = 55  # never keep the user waiting longer than this for reactions
GRACE_S = 6  # once most customers answered, wait this long for the rest
ENOUGH = 0.9


async def react(persona: dict, product: dict, image: types.Part | None) -> dict | None:
    _, temperature = CONFIG["p04_simulate"]
    system, user = render(
        "p04_simulate",
        persona_json=json.dumps(persona["profile"], ensure_ascii=False),
        product_name=product["name"],
        product_description=product["description"],
        price_inr=_price_text(product["price_inr"]),
        pack_size=product["pack_size"],
        channel=product["channel"],
        competitors=product.get("competitors") or NOT_STATED,
    )
    for _ in range(2):  # first attempt + one retry for stalled or failed calls
        data, ok = await generate_json(system=system, user=user, fallback=None, temperature=temperature,
                                       images=[image] if image else None, timeout_s=CALL_TIMEOUT_S)
        row = normalise(data, persona) if ok else None
        if row:
            return row
    return None


async def run_reactions(personas: list[dict], product: dict, image: types.Part | None) -> tuple[list[dict], dict]:
    """Returns (rows that succeeded, run info). Stragglers are dropped rather than delaying everyone."""
    loop = asyncio.get_running_loop()
    started = loop.time()
    tasks = [asyncio.create_task(react(p, product, image)) for p in personas]
    pending = set(tasks)
    enough_at: float | None = None
    while pending:
        now = loop.time()
        deadline = started + TEST_BUDGET_S
        if enough_at is not None:
            deadline = min(deadline, enough_at + GRACE_S)
        if now >= deadline:
            break
        _, pending = await asyncio.wait(pending, timeout=deadline - now, return_when=asyncio.FIRST_COMPLETED)
        if enough_at is None and len(tasks) - len(pending) >= ENOUGH * len(tasks):
            enough_at = loop.time()
    for t in pending:
        t.cancel()
    rows = [t.result() for t in tasks if t.done() and not t.cancelled() and t.exception() is None and t.result()]
    run = {
        "mode": "live",
        "personas": len(rows),
        "personas_asked": len(personas),
        "gemini_calls": len(personas),
        "duration_s": round(loop.time() - started, 1),
        "model": get_settings().gemini_flash_model,
    }
    return rows, run
