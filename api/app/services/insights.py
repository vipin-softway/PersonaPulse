"""Prompt 6 (insights summary) and Prompt 7 (improved variants), with output validation.

Numbers are computed first (aggregate.py) and passed in, so Gemini explains
the data rather than calculating it. Both functions return None on failure;
the dashboard simply hides the section.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.prompts import CONFIG, render
from app.services.gemini import generate_json

PRO_TIMEOUT_S = 85  # primary Pro model gets ~47 s, the fallback the rest
NO_CONSTRAINTS = "None stated"
VERDICTS = {"launch", "launch_with_changes", "rethink"}


def _s(v: Any, limit: int = 400) -> str:
    return str(v or "").strip()[:limit]


def _list(v: Any, limit: int = 5) -> list:
    return v[:limit] if isinstance(v, list) else []


def product_summary(product: dict) -> str:
    price = int(product["price_inr"]) if float(product["price_inr"]).is_integer() else product["price_inr"]
    return f"{product['name']}: {product['description']} Price ₹{price}, pack size {product['pack_size']}, sold via {product['channel']}."


def product_fields(product: dict) -> dict:
    """The product exactly as Prompt 4 sees it (Prompt 7's {{product_summary_json}})."""
    return {"product_name": product["name"], "product_description": product["description"],
            "price_inr": product["price_inr"], "pack_size": product["pack_size"], "channel": product["channel"]}


def _segment_stats(variant: dict) -> list[dict]:
    return [{"segment_name": s["segment_name"], "persona_count": s["n"], "average_intent_1_to_5": s["avg_intent"],
             "pct_yes": s["would_buy_pct"], "pct_maybe": s["maybe_pct"], "pct_no": s["no_pct"],
             "median_willingness_to_pay_inr": s["median_wtp_inr"]} for s in variant["segments"]]


def _sample_quotes(rows: list[dict], per_segment: int = 3, limit: int = 15) -> list[dict]:
    """A spread of quotes: up to 3 per segment, mixing yes / maybe / no."""
    by_seg: dict[str, list[dict]] = {}
    for r in rows:
        by_seg.setdefault(r.get("segment_name") or "", []).append(r)
    out = []
    for seg, items in by_seg.items():
        items = sorted(items, key=lambda r: ("yes", "maybe", "no").index(r.get("would_buy", "no")))
        picked, seen = [], set()
        for r in items:  # one of each decision first
            if r.get("would_buy") not in seen:
                picked.append(r)
                seen.add(r.get("would_buy"))
        picked += [r for r in items if r not in picked]
        out += [{"segment": seg, "would_buy": r.get("would_buy"), "quote": r.get("quote")} for r in picked[:per_segment]]
    return out[:limit]


def _clean_insights(d: Any) -> dict | None:
    if not isinstance(d, dict) or not _s(d.get("headline")):
        return None
    verdict = _s(d.get("overall_verdict")).lower()
    return {
        "headline": _s(d.get("headline"), 300),
        "overall_verdict": verdict if verdict in VERDICTS else "launch_with_changes",
        "best_segments": [{"segment_name": _s(x.get("segment_name"), 80), "why": _s(x.get("why"), 300)}
                          for x in _list(d.get("best_segments"), 3) if isinstance(x, dict)],
        "weakest_segments": [{"segment_name": _s(x.get("segment_name"), 80), "why": _s(x.get("why"), 300)}
                             for x in _list(d.get("weakest_segments"), 3) if isinstance(x, dict)],
        "price_insight": _s(d.get("price_insight"), 500),
        "top_3_objections": [{"objection": _s(x.get("objection"), 200),
                              "segments_affected": [_s(y, 80) for y in _list(x.get("segments_affected"))]}
                             for x in _list(d.get("top_3_objections"), 3) if isinstance(x, dict)],
        "top_3_strengths": [_s(x, 200) for x in _list(d.get("top_3_strengths"), 3)],
        "standout_quotes": [_s(x, 400) for x in _list(d.get("standout_quotes"), 3)],
        "recommended_target_segment": _s(d.get("recommended_target_segment"), 200),
        "caveat": _s(d.get("caveat"), 300) or "These are AI-simulated customers; validate with real customers.",
    }


async def summarize(product: dict, variant: dict, rows: list[dict]) -> dict | None:
    """Prompt 6 for one variant. `rows` carry segment_name (see tests_store.with_display)."""
    system, user = render(
        "p06_insights",
        product_summary=product_summary(product),
        segment_stats_json=json.dumps(_segment_stats(variant), ensure_ascii=False),
        top_objections_json=json.dumps(variant["top_objections"], ensure_ascii=False),
        top_likes_json=json.dumps(variant["top_likes"], ensure_ascii=False),
        sample_quotes_json=json.dumps(_sample_quotes(rows), ensure_ascii=False),
        focus_group_json="{}",
    )
    data, ok = await generate_json(system=system, user=user, fallback=None, model=get_settings().gemini_pro_model,
                                   temperature=CONFIG["p06_insights"][1], timeout_s=PRO_TIMEOUT_S)
    return _clean_insights(data) if ok else None


def _clean_variant(d: Any, n: int) -> dict | None:
    if not isinstance(d, dict):
        return None
    up = d.get("updated_product") if isinstance(d.get("updated_product"), dict) else {}
    try:
        price = float(str(up.get("price_inr")).replace("₹", "").replace(",", ""))
    except (TypeError, ValueError):
        return None
    name, desc = _s(up.get("product_name"), 80), _s(up.get("product_description"), 600)
    if price <= 0 or not name or not desc or not _s(d.get("title")):
        return None
    return {
        "variant_id": f"v{n}",  # our own ids, so they never clash with "original" or each other
        "title": _s(d.get("title"), 120),
        "changes": [_s(x, 160) for x in _list(d.get("changes"), 3)],
        "objections_addressed": [_s(x, 160) for x in _list(d.get("objections_addressed"), 4)],
        "expected_effect": _s(d.get("expected_effect"), 400),
        "risk": _s(d.get("risk"), 300),
        "updated_product": {"product_name": name, "product_description": desc, "price_inr": price,
                            "pack_size": _s(up.get("pack_size"), 60) or "1 unit",
                            "channel": _s(up.get("channel"), 60) or "E-commerce marketplace"},
        "imagen_prompt": _s(d.get("imagen_prompt"), 600) or None,
    }


async def suggest(product: dict, insights: dict | None, constraints: str | None) -> list[dict] | None:
    """Prompt 7: up to 3 improved variants."""
    system, user = render(
        "p07_improve",
        product_summary_json=json.dumps(product_fields(product), ensure_ascii=False),
        insights_json=json.dumps(insights or {}, ensure_ascii=False),
        constraints=(constraints or "").strip() or NO_CONSTRAINTS,
    )
    data, ok = await generate_json(system=system, user=user, fallback=None, model=get_settings().gemini_pro_model,
                                   temperature=CONFIG["p07_improve"][1], timeout_s=PRO_TIMEOUT_S)
    if not ok or not isinstance(data, dict):
        return None
    variants = [v for v in (_clean_variant(x, i) for i, x in enumerate(_list(data.get("variants"), 3), start=1)) if v]
    return variants or None
