"""Turn per-persona simulation rows into the dashboard shape the web app reads.

Pure functions, no I/O: the same code aggregates live tests (rows from
BigQuery) and builds the bundled demo, so both look identical in the UI.

Input row fields mirror the `simulation_results` table (Prompt 4 output), plus
persona/segment display fields joined in: persona_name, age, city, segment_name.
`would_buy` is "yes" | "maybe" | "no"; headline "would buy" means "yes".
"""

from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any, Iterable

TOP_N = 6
MAX_QUOTES = 8


def would_buy(r: dict) -> str:
    v = r.get("would_buy")
    if isinstance(v, bool):
        return "yes" if v else "no"
    v = str(v or "").strip().lower()
    return v if v in ("yes", "maybe", "no") else "no"


def _mix(rows: list[dict]) -> dict:
    n = len(rows)
    return {k: _pct(sum(would_buy(r) == k for r in rows), n) for k in ("yes", "maybe", "no")}


def _median(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(median(vals)) if vals else None


def _pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def _avg(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(mean(vals), 2) if vals else None


def _top(rows: list[dict], field: str) -> list[dict]:
    counts: Counter[str] = Counter()
    for r in rows:
        # Count each theme once per persona.
        for item in {str(x).strip() for x in (r.get(field) or []) if str(x).strip()}:
            counts[item] += 1
    return [
        {"text": text, "count": c, "pct": _pct(c, len(rows))}
        for text, c in counts.most_common(TOP_N)
    ]


def _quotes(rows: list[dict]) -> list[dict]:
    """A balanced mix: half buyers, half non-buyers, spread across segments, no repeated quotes."""
    buyers = sorted((r for r in rows if would_buy(r) == "yes"), key=lambda r: -(r.get("purchase_intent") or 0))
    others = sorted((r for r in rows if would_buy(r) != "yes"), key=lambda r: r.get("purchase_intent") or 0)
    picked: list[dict] = []
    seen_quotes: set[str] = set()

    def take(pool: list[dict], limit: int, per_segment: int) -> None:
        segs: Counter[str] = Counter(r.get("segment_id") for r in picked if r in pool)
        for r in pool:
            if len(picked) >= MAX_QUOTES or limit <= 0:
                return
            q = (r.get("quote") or "").strip()
            if not q or q in seen_quotes or r in picked or segs[r.get("segment_id")] >= per_segment:
                continue
            picked.append(r)
            seen_quotes.add(q)
            segs[r.get("segment_id")] += 1
            limit -= 1

    half = MAX_QUOTES // 2
    take(buyers, half, 1)
    take(others, half, 1)
    # Top up from whichever group still has distinct quotes.
    take(buyers, MAX_QUOTES, 2)
    take(others, MAX_QUOTES, 2)
    picked.sort(key=lambda r: ("yes", "maybe", "no").index(would_buy(r)))
    return [
        {
            "persona_id": r.get("persona_id"),
            "persona_name": r.get("persona_name"),
            "age": r.get("age"),
            "city": r.get("city"),
            "segment_name": r.get("segment_name"),
            "would_buy": would_buy(r),
            "purchase_intent": r.get("purchase_intent"),
            "main_reason": r.get("main_reason"),
            "quote": r.get("quote"),
        }
        for r in picked
    ]


def _price(rows: list[dict], price_inr: float) -> dict:
    wtps = [r["willingness_to_pay_inr"] for r in rows if r.get("willingness_to_pay_inr") is not None]
    if not wtps or price_inr <= 0:
        return {"price_inr": price_inr, "median_wtp_inr": None, "pct_wtp_at_or_above_price": None, "buckets": []}
    # Buckets are anchored on the price, so each one is wholly below or at/above it.
    step = max(5, round(price_inr / 5 / 5) * 5)
    buckets: Counter[int] = Counter(int((w - price_inr) // step) for w in wtps)
    return {
        "price_inr": price_inr,
        "median_wtp_inr": round(median(wtps)),
        "pct_wtp_at_or_above_price": _pct(sum(w >= price_inr for w in wtps), len(wtps)),
        "buckets": [
            {"from_inr": max(0, price_inr + k * step), "to_inr": price_inr + (k + 1) * step, "count": buckets[k]}
            for k in range(min(buckets), max(buckets) + 1)
            if price_inr + (k + 1) * step > 0
        ],
    }


def aggregate_variant(variant: str, product: dict, rows: list[dict], segments: list[dict]) -> dict:
    """Aggregate one variant's persona rows. `segments` gives id/name/share for ordering."""
    n = len(rows)
    by_seg: dict[str, list[dict]] = {}
    for r in rows:
        by_seg.setdefault(r.get("segment_id"), []).append(r)

    seg_out = []
    for s in segments:
        srows = by_seg.get(s["segment_id"], [])
        if not srows:
            continue
        seg_out.append(
            {
                "segment_id": s["segment_id"],
                "segment_name": s["name"],
                "share": s.get("share"),
                "n": len(srows),
                "would_buy_pct": _mix(srows)["yes"],
                "maybe_pct": _mix(srows)["maybe"],
                "no_pct": _mix(srows)["no"],
                "avg_intent": _avg(r.get("purchase_intent") for r in srows),
                "avg_wtp_inr": _avg(r.get("willingness_to_pay_inr") for r in srows),
                "median_wtp_inr": _median(r.get("willingness_to_pay_inr") for r in srows),
            }
        )

    return {
        "variant": variant,
        "product": product,
        "n_personas": n,
        "overall": {
            "would_buy_pct": _mix(rows)["yes"],
            "maybe_pct": _mix(rows)["maybe"],
            "avg_intent": _avg(r.get("purchase_intent") for r in rows),
            "avg_wtp_inr": _avg(r.get("willingness_to_pay_inr") for r in rows),
        },
        "segments": seg_out,
        "price": _price(rows, float(product.get("price_inr") or 0)),
        "top_objections": _top(rows, "top_objections"),
        "top_likes": _top(rows, "top_likes"),
        "quotes": _quotes(rows),
        "insights": None,  # Prompt 6 output
    }


def build_test_result(
    test_id: str,
    variants: list[dict[str, Any]],
    *,
    created_at: str,
    is_demo: bool = False,
    is_placeholder: bool = False,
    suggestions: list[dict] | None = None,  # Prompt 7 "variants"
) -> dict:
    return {
        "test_id": test_id,
        "label": "AI-simulated customers",
        "created_at": created_at,
        "is_demo": is_demo,
        "is_placeholder": is_placeholder,
        "variants": variants,
        "suggestions": suggestions or [],
    }
