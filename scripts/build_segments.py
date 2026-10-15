"""Prompt 2: discover 4-7 customer segments from a sample of review signals.

Runs once per customer panel: reads that panel's signals from
data/processed/signals.jsonl, sends ~500 to Gemini Pro, normalises shares to
100%, and saves data/processed/segments_<panel>.json. Then loads every
panel's segments into BigQuery table segments.

    python build_segments.py --dry-run       # show prompt sizes, no Gemini call
    python build_segments.py                 # all panels
    python build_segments.py --panel home    # one panel (others' saved files are kept)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

from common import PROCESSED, call_prompt, load_json_to_bq, preview_prompt
from app.panels import PANELS

SAMPLE = 500


def compact(sig: dict) -> dict:
    """Drop empty fields and bookkeeping to keep the prompt small."""
    keep = ("review_id", "priorities", "likes", "complaints", "usage_context", "price_sensitivity", "sentiment",
            "purchase_trigger", "dealbreaker")
    return {k: sig[k] for k in keep if sig.get(k) not in (None, [], "")}


def validate(segments: list[dict], known_ids: set[str], panel: str) -> list[dict]:
    segments = [s for s in segments if isinstance(s, dict) and s.get("name")]
    if not 2 <= len(segments) <= 8:
        raise ValueError(f"Gemini returned {len(segments)} segments; expected 4-7")
    total = sum(float(s.get("share_percent") or 0) for s in segments) or len(segments)
    for i, s in enumerate(segments, start=1):
        s["segment_id"] = f"{panel}_seg_{i}"  # stable ids regardless of what the model wrote
        s["share_percent"] = round(100 * float(s.get("share_percent") or total / len(segments)) / total, 1)
        s["representative_review_ids"] = [r for r in s.get("representative_review_ids") or [] if r in known_ids]
    return segments


async def build_panel(panel: str, signals: list[dict], seed: int, dry_run: bool) -> None:
    category = PANELS[panel]["category"]
    mine = [s for s in signals if s.get("panel") == panel]
    # Signals with no decision content don't help segmentation.
    informative = [s for s in mine if s.get("priorities") or s.get("complaints")]
    if not informative:
        print(f"[{panel}] no signals yet; run extract_signals.py first")
        return
    sample = random.Random(seed).sample(informative, min(SAMPLE, len(informative)))
    payload = json.dumps([compact(s) for s in sample], ensure_ascii=False)
    print(f"[{panel}] {len(mine)} signals, {len(informative)} informative, sending {len(sample)} ({len(payload):,} chars)")
    if dry_run:
        print(preview_prompt("p02_segments", category=category, signals_sample_json=payload)[:800] + "\n...")
        return

    data, ok = await call_prompt("p02_segments", fallback={"segments": []}, timeout_s=300,
                                 category=category, signals_sample_json=payload)
    if not ok:
        print(f"[{panel}] Prompt 2 failed (see warning above). Rerun with --panel {panel}.")
        return
    try:
        segments = validate(data.get("segments") or [], {s["review_id"] for s in mine}, panel)
    except ValueError as e:
        print(f"[{panel}] {e}. Rerun with --panel {panel}.")
        return
    for s in segments:
        s["panel"] = panel
    (PROCESSED / f"segments_{panel}.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    for s in segments:
        print(f"  {s['segment_id']:18} {s['share_percent']:5.1f}%  {s['name']}  ({s.get('price_sensitivity')} price sensitivity)")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", choices=list(PANELS), help="only this panel (default: all)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-bq", action="store_true")
    args = ap.parse_args()

    signals = [json.loads(l) for l in (PROCESSED / "signals.jsonl").read_text(encoding="utf-8").splitlines()]
    panels = [args.panel] if args.panel else list(PANELS)
    await asyncio.gather(*(build_panel(p, signals, args.seed, args.dry_run) for p in panels))
    if args.dry_run or args.no_bq:
        return

    # Load every panel's saved segments together (the BigQuery load replaces the table).
    from app.config import get_settings

    now, model = datetime.now(timezone.utc).isoformat(), get_settings().gemini_pro_model
    rows = []
    for p in PANELS:
        f = PROCESSED / f"segments_{p}.json"
        if f.exists():
            rows += [
                {"segment_id": s["segment_id"], "panel": p, "name": s["name"], "description": s.get("description"),
                 "share": s["share_percent"] / 100, "price_sensitivity": s.get("price_sensitivity"), "profile": s,
                 "model": model, "created_at": now}
                for s in json.loads(f.read_text(encoding="utf-8"))
            ]
    load_json_to_bq("segments", rows)


if __name__ == "__main__":
    asyncio.run(main())
