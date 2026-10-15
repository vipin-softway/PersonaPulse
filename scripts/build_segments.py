"""Prompt 2: discover 4-7 customer segments from a sample of review signals.

Reads data/processed/signals.jsonl (from extract_signals.py), sends ~500
signals to Gemini Pro once, normalises shares to 100%, and saves
data/processed/segments.json plus BigQuery table segments.

    python build_segments.py --dry-run     # show prompt size, no Gemini call
    python build_segments.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

from common import PROCESSED, call_prompt, load_json_to_bq, preview_prompt

CATEGORY = "electronics accessories"
SAMPLE = 500


def compact(sig: dict) -> dict:
    """Drop empty fields and bookkeeping to keep the prompt small."""
    keep = ("review_id", "priorities", "likes", "complaints", "usage_context", "price_sensitivity", "sentiment",
            "purchase_trigger", "dealbreaker")
    return {k: sig[k] for k in keep if sig.get(k) not in (None, [], "")}


def validate(segments: list[dict], known_ids: set[str]) -> list[dict]:
    segments = [s for s in segments if isinstance(s, dict) and s.get("name")]
    if not 2 <= len(segments) <= 8:
        raise SystemExit(f"Gemini returned {len(segments)} segments; expected 4-7. Rerun build_segments.py.")
    total = sum(float(s.get("share_percent") or 0) for s in segments) or len(segments)
    for i, s in enumerate(segments, start=1):
        s["segment_id"] = f"seg_{i}"  # stable ids regardless of what the model wrote
        s["share_percent"] = round(100 * float(s.get("share_percent") or total / len(segments)) / total, 1)
        s["representative_review_ids"] = [r for r in s.get("representative_review_ids") or [] if r in known_ids]
    return segments


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-bq", action="store_true")
    args = ap.parse_args()

    signals = [json.loads(l) for l in (PROCESSED / "signals.jsonl").read_text(encoding="utf-8").splitlines()]
    # Signals with no decision content don't help segmentation.
    informative = [s for s in signals if s.get("priorities") or s.get("complaints")]
    sample = random.Random(args.seed).sample(informative, min(SAMPLE, len(informative)))
    payload = json.dumps([compact(s) for s in sample], ensure_ascii=False)
    print(f"{len(signals)} signals, {len(informative)} informative, sending {len(sample)} ({len(payload):,} chars)")

    if args.dry_run:
        print(preview_prompt("p02_segments", category=CATEGORY, signals_sample_json=payload)[:1500] + "\n...")
        return

    data, ok = await call_prompt("p02_segments", fallback={"segments": []}, timeout_s=300,
                                 category=CATEGORY, signals_sample_json=payload)
    if not ok:
        raise SystemExit("Prompt 2 failed (see warning above). Rerun build_segments.py.")
    segments = validate(data.get("segments") or [], {s["review_id"] for s in signals})

    (PROCESSED / "segments.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    for s in segments:
        print(f"  {s['segment_id']}  {s['share_percent']:5.1f}%  {s['name']}  ({s.get('price_sensitivity')} price sensitivity)")

    if args.no_bq:
        return
    from app.config import get_settings

    now, model = datetime.now(timezone.utc).isoformat(), get_settings().gemini_pro_model
    load_json_to_bq("segments", [
        {"segment_id": s["segment_id"], "name": s["name"], "description": s.get("description"),
         "share": s["share_percent"] / 100, "price_sensitivity": s.get("price_sensitivity"), "profile": s,
         "model": model, "created_at": now}
        for s in segments
    ])


if __name__ == "__main__":
    asyncio.run(main())
