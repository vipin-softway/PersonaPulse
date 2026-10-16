"""Prompt 9: look a product up on the web (Gemini + Google Search grounding) to fill the test form.

Grounded calls can't use JSON output mode reliably, so the prompt asks for JSON
and the reply is parsed like any other. Returns the cleaned fields plus the
searches Gemini ran, so the UI can show where the details came from.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from google.genai import types

from app.config import get_settings
from app.panels import PANELS
from app.prompts import CONFIG, render
from app.services.gemini import _client, _parse_json, _sem

log = logging.getLogger("personapulse.lookup")

TIMEOUT_S = 45  # low thinking: ~5-15 s with 2-3 searches (default thinking took ~55 s)
MARKET = "India"
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_S = 3600


def panels_json() -> str:
    return json.dumps([
        {"id": pid, "shoppers": p["shoppers"], "example_products": p["examples"],
         "typical_price_range_inr": f"{p['price_p10']}-{p['price_p90']}"}
        for pid, p in PANELS.items()
    ], ensure_ascii=False)


def _num(v: Any) -> float | None:
    try:
        f = float(str(v).replace("₹", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _short(text: str, n: int) -> str:
    """Trim to n chars at a natural break ("1 unit (13.6-inch laptop ...)" -> "1 unit")."""
    text = " ".join(text.split())
    if len(text) <= n:
        return text
    head = text.split(" (")[0].split(", ")[0]
    return head if 0 < len(head) <= n else text[:n].rsplit(" ", 1)[0]


def _clean(d: Any) -> dict | None:
    if not isinstance(d, dict):
        return None
    if not d.get("found", True) or not str(d.get("product_name") or "").strip():
        return {"found": False, "notes": str(d.get("notes") or "We couldn't identify that product.")[:300]}
    comps = []
    for c in d.get("competitors") or []:
        if isinstance(c, dict) and str(c.get("name") or "").strip():
            price = _num(c.get("price_inr"))
            comps.append({"name": str(c["name"]).strip()[:80], "price_inr": price})
    comps = comps[:5]
    panel = d.get("suggested_panel") if d.get("suggested_panel") in PANELS else None
    fit = str(d.get("panel_fit") or "").lower()
    return {
        "found": True,
        "product_name": str(d["product_name"]).strip()[:80],
        "product_description": str(d.get("product_description") or "").strip()[:600],
        "price_inr": _num(d.get("price_inr")),
        "pack_size": _short(str(d.get("pack_size") or ""), 60) or "1 unit",
        "channel": str(d.get("channel") or "").strip()[:60],
        "competitors": comps,
        "competitors_text": ", ".join(
            f"{c['name']} ₹{int(c['price_inr']):,}" if c["price_inr"] else c["name"] for c in comps)[:200],
        "suggested_panel": panel,
        "panel_fit": fit if fit in ("good", "stretch", "poor") else None,
        "notes": str(d.get("notes") or "").strip()[:300],
    }


async def lookup(query: str) -> dict | None:
    """Returns cleaned product details, {"found": False, ...}, or None if the lookup failed."""
    key = " ".join(query.lower().split())
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < _CACHE_S:
        return hit[1]

    system, user = render("p09_lookup", product_query=query, market=MARKET, panels_json=panels_json())
    config = types.GenerateContentConfig(
        system_instruction=system, temperature=CONFIG["p09_lookup"][1],
        tools=[types.Tool(google_search=types.GoogleSearch())],
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )
    model = get_settings().gemini_flash_model
    for attempt in (1, 2):  # one retry on invalid JSON or a failed call
        try:
            async with _sem():
                resp = await asyncio.wait_for(
                    _client().aio.models.generate_content(model=model, contents=[user], config=config), TIMEOUT_S)
            result = _clean(_parse_json(resp.text))
            if result is None:
                raise ValueError("unexpected shape")
            gm = resp.candidates[0].grounding_metadata if resp.candidates else None
            result["searched"] = list((gm.web_search_queries if gm else None) or [])[:6]
            result["sources"] = [{"title": ch.web.title, "url": ch.web.uri}
                                 for ch in ((gm.grounding_chunks if gm else None) or []) if ch.web][:5]
            _cache[key] = (time.monotonic(), result)
            return result
        except asyncio.TimeoutError:
            log.warning("Lookup timed out after %ss for %r", TIMEOUT_S, query)
            return None
        except Exception as e:  # noqa: BLE001
            log.warning("Lookup attempt %d failed for %r: %s", attempt, query, e)
    return None
