"""Prompt 1: extract structured customer signals from every training review.

Reads data/processed/reviews.csv (from load_reviews.py), skips hidden back-test
products, sends batches of 20 reviews to Gemini Flash in parallel, and saves
results to data/processed/signals.jsonl as it goes, so a rerun resumes where
it stopped. Finally loads everything into BigQuery review_signals.

    python extract_signals.py --dry-run          # print the first prompt, no Gemini calls
    python extract_signals.py --limit 40         # quick real test on 2 batches
    python extract_signals.py                    # full run (~110 calls)
    python extract_signals.py --holdout-only     # signals for hidden products (back-test complaint check)
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

import pandas as pd

from common import PROCESSED, call_prompt, load_json_to_bq, preview_prompt

CATEGORY = "electronics accessories"
BATCH = 20
PRIORITIES = {"price", "value_for_money", "quality", "durability", "performance", "design", "comfort", "taste", "health",
              "brand", "convenience", "delivery", "packaging", "customer_service", "features", "eco_friendly"}


def review_payload(r) -> dict:
    text = f"{r.review_title}. {r.review_content}" if isinstance(r.review_title, str) and r.review_title else r.review_content
    return {"review_id": r.review_id, "product_name": r.product_name[:120], "price_inr": r.price_inr,
            "rating": r.product_rating, "review_text": text}


def tidy(sig: dict) -> dict:
    """Keep the schema tight: known priorities only, max 3 likes/complaints."""
    sig["priorities"] = [p for p in sig.get("priorities") or [] if p in PRIORITIES]
    sig["likes"] = (sig.get("likes") or [])[:3]
    sig["complaints"] = (sig.get("complaints") or [])[:3]
    return sig


async def run_batch(batch: list[dict], i: int, total: int) -> list[dict]:
    data, ok = await call_prompt("p01_signals", fallback={"signals": []}, category=CATEGORY,
                                 reviews_json=json.dumps(batch, ensure_ascii=False))
    wanted = {r["review_id"] for r in batch}
    signals = [tidy(s) for s in (data.get("signals") or []) if isinstance(s, dict) and s.get("review_id") in wanted]
    print(f"  batch {i + 1}/{total}: {len(signals)}/{len(batch)} signals{'' if ok else '  (FAILED, will retry on rerun)'}")
    return signals


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only process this many reviews")
    ap.add_argument("--holdout-only", action="store_true", help="hidden products instead of training reviews")
    ap.add_argument("--no-bq", action="store_true", help="skip the BigQuery load")
    args = ap.parse_args()

    reviews = pd.read_csv(PROCESSED / "reviews.csv")
    reviews = reviews[reviews.is_holdout == args.holdout_only]
    out_file = PROCESSED / ("signals_holdout.jsonl" if args.holdout_only else "signals.jsonl")

    done: dict[str, dict] = {}
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8").splitlines():
            s = json.loads(line)
            done[s["review_id"]] = s
    todo = [review_payload(r) for r in reviews.itertuples(index=False) if r.review_id not in done]
    if args.limit:
        todo = todo[: args.limit]
    batches = [todo[i : i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{len(done)} reviews already done, {len(todo)} to process in {len(batches)} batches")

    if args.dry_run:
        if batches:
            print(preview_prompt("p01_signals", category=CATEGORY, reviews_json=json.dumps(batches[0][:3], ensure_ascii=False)))
        return

    product_of = dict(zip(reviews.review_id, reviews.product_id))
    now = datetime.now(timezone.utc).isoformat()
    with out_file.open("a", encoding="utf-8") as f:
        for coro in asyncio.as_completed([run_batch(b, i, len(batches)) for i, b in enumerate(batches)]):
            for s in await coro:
                s.update(product_id=product_of.get(s["review_id"]), created_at=now)
                done[s["review_id"]] = s
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
            f.flush()

    print(f"{len(done)} / {len(reviews)} reviews have signals")
    if args.no_bq or args.holdout_only:
        return
    from app.config import get_settings

    model = get_settings().gemini_flash_model
    load_json_to_bq("review_signals", [
        {"review_id": s["review_id"], "product_id": s.get("product_id"), "signals": s,
         "price_sensitivity": s.get("price_sensitivity"), "sentiment": s.get("sentiment"),
         "usage_context": s.get("usage_context"), "model": model, "created_at": s.get("created_at")}
        for s in done.values()
    ])


if __name__ == "__main__":
    asyncio.run(main())
