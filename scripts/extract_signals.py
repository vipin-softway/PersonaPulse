"""Prompt 1: extract structured customer signals from every training review.

Reads data/processed/reviews.csv (from load_reviews.py), skips hidden back-test
products, sends batches of 20 reviews (one panel per batch, so {{category}}
matches) to Gemini Flash in parallel, and saves
results to data/processed/signals.jsonl as it goes, so a rerun resumes where
it stopped. Finally loads everything into BigQuery review_signals.

    python extract_signals.py --dry-run          # print the first prompt, no Gemini calls
    python extract_signals.py --limit 40         # quick real test on 2 batches
    python extract_signals.py                    # full run, all panels (~340 calls)
    python extract_signals.py --panel home       # one panel only
    python extract_signals.py --holdout-only     # signals for hidden products (back-test complaint check)
    python extract_signals.py --engine bigquery --panel home
        # BigQuery AI: run Prompt 1 inside BigQuery with AI.GENERATE_TEXT (run setup_bqai.sh once first)
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

import pandas as pd

from common import PROCESSED, call_prompt, load_json_to_bq, preview_prompt
from app.panels import PANELS

BATCH = 20
PRIORITIES = {"price", "value_for_money", "quality", "durability", "performance", "design", "comfort", "taste", "health",
              "brand", "convenience", "delivery", "packaging", "customer_service", "features", "eco_friendly"}


def parse_signals(data: dict, batch: list[dict]) -> list[dict]:
    wanted = {r["review_id"] for r in batch}
    return [tidy(s) for s in (data.get("signals") or []) if isinstance(s, dict) and s.get("review_id") in wanted]


def run_bigquery(batches: list[tuple[str, list[dict]]]) -> tuple[dict[int, list[dict]], list[int]]:
    """Prompt 1 via BigQuery AI. Returns ({batch index: signals}, failed batch indexes)."""
    from app.prompts import CONFIG, render
    from app.services.gemini import _parse_json

    import bqai

    rows, system = [], None
    for i, (panel, batch) in enumerate(batches):
        system, user = render("p01_signals", category=PANELS[panel]["category"], reviews_json=json.dumps(batch, ensure_ascii=False))
        rows.append({"batch_id": str(i), "prompt": user})
    print(f"Sending {len(rows)} batches to BigQuery AI (AI.GENERATE_TEXT)...")
    replies = bqai.generate(rows, system, temperature=CONFIG["p01_signals"][1])

    results, failed = {}, []
    for i, (panel, batch) in enumerate(batches):
        text, status = replies.get(str(i), (None, "missing"))
        try:
            results[i] = parse_signals(_parse_json(text), batch)
        except (ValueError, TypeError):
            failed.append(i)
            print(f"  batch {i + 1} [{panel}] failed in BigQuery ({status or 'invalid JSON'}); retrying in Python")
    return results, failed


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


async def run_batch(panel: str, batch: list[dict], i: int, total: int) -> list[dict]:
    data, ok = await call_prompt("p01_signals", fallback={"signals": []}, category=PANELS[panel]["category"],
                                 reviews_json=json.dumps(batch, ensure_ascii=False))
    signals = parse_signals(data, batch)
    print(f"  batch {i + 1}/{total} [{panel}]: {len(signals)}/{len(batch)} signals{'' if ok else '  (FAILED, will retry on rerun)'}")
    return signals


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only process this many reviews")
    ap.add_argument("--holdout-only", action="store_true", help="hidden products instead of training reviews")
    ap.add_argument("--panel", choices=list(PANELS), help="only this panel (default: all)")
    ap.add_argument("--engine", choices=["python", "bigquery"], default="python",
                    help="python: parallel Vertex AI calls; bigquery: BigQuery AI (AI.GENERATE_TEXT)")
    ap.add_argument("--no-bq", action="store_true", help="skip the BigQuery load")
    args = ap.parse_args()

    reviews = pd.read_csv(PROCESSED / "reviews.csv")
    reviews = reviews[reviews.is_holdout == args.holdout_only]
    if args.panel:
        reviews = reviews[reviews.panel == args.panel]
    out_file = PROCESSED / ("signals_holdout.jsonl" if args.holdout_only else "signals.jsonl")

    done: dict[str, dict] = {}
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8").splitlines():
            s = json.loads(line)
            done[s["review_id"]] = s
    todo = [r for r in reviews.itertuples(index=False) if r.review_id not in done]
    if args.limit:
        todo = todo[: args.limit]
    batches: list[tuple[str, list[dict]]] = []
    for panel in PANELS:
        items = [review_payload(r) for r in todo if r.panel == panel]
        batches += [(panel, items[i : i + BATCH]) for i in range(0, len(items), BATCH)]
    print(f"{len(done)} reviews already done, {len(todo)} to process in {len(batches)} batches")

    if args.dry_run:
        if batches:
            panel, first = batches[0]
            print(preview_prompt("p01_signals", category=PANELS[panel]["category"], reviews_json=json.dumps(first[:3], ensure_ascii=False)))
        return

    product_of = dict(zip(reviews.review_id, reviews.product_id))
    panel_of = dict(zip(reviews.review_id, reviews.panel))
    now = datetime.now(timezone.utc).isoformat()
    def save(f, signals: list[dict], engine: str) -> None:
        for s in signals:
            s.update(product_id=product_of.get(s["review_id"]), panel=panel_of.get(s["review_id"]), engine=engine, created_at=now)
            done[s["review_id"]] = s
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
        f.flush()

    with out_file.open("a", encoding="utf-8") as f:
        todo_idx = list(range(len(batches)))
        if args.engine == "bigquery" and batches:
            results, todo_idx = run_bigquery(batches)
            for signals in results.values():
                save(f, signals, "bigquery_ai")
            print(f"BigQuery AI: {sum(len(v) for v in results.values())} signals; {len(todo_idx)} batch(es) left for Python")
        jobs = [run_batch(batches[i][0], batches[i][1], i, len(batches)) for i in todo_idx]
        for coro in asyncio.as_completed(jobs):
            save(f, await coro, "vertex_python")

    print(f"{sum(r in done for r in reviews.review_id)} / {len(reviews)} reviews have signals")
    if args.no_bq or args.holdout_only:
        return
    from app.config import get_settings

    model = get_settings().gemini_flash_model
    load_json_to_bq("review_signals", [
        {"review_id": s["review_id"], "panel": s.get("panel"), "product_id": s.get("product_id"), "signals": s,
         "price_sensitivity": s.get("price_sensitivity"), "sentiment": s.get("sentiment"),
         "usage_context": s.get("usage_context"), "model": model, "created_at": s.get("created_at")}
        for s in done.values()
    ])


if __name__ == "__main__":
    asyncio.run(main())
