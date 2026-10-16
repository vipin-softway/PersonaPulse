"""Prompt 8 back-test: can the AI customers predict ratings of products they've never seen?

The 10 hidden accessories products (holdout_products.json) were removed before
personas were built. Every accessories persona "buys and uses" each one
(name, description and price only; never its reviews or rating) and predicts
a star rating. Scoring follows docs/prompts.md:

1. Weighted average predicted rating per product (weight = segment share).
2. Mean absolute error vs the real average rating, and correlation.
3. Complaint overlap: how many of the top 3 real complaints (real reviews
   through Prompt 1) appear in the top 5 predicted complaints.
4. A naive baseline: the average rating of the products personas were built from.

AI personas rate more harshly than Amazon reviewers (about 0.9 stars here), so
we also report a calibrated error: each product's prediction is shifted by the
average offset measured on the OTHER hidden products (leave-one-out), so no
product's own rating is used to correct it. And pairwise ranking accuracy:
for every pair of hidden products, did the AI customers prefer the one that
real buyers rated higher? The constant baseline can't rank at all.

    python run_backtest.py --dry-run
    python run_backtest.py                 # ~1,000 Flash calls, ~10 min
    python run_backtest.py --rescore       # recompute metrics from backtest.json, no Gemini calls
Outputs BigQuery backtest_results and api/app/data/backtest.json (served by GET /backtest).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import correlation, mean

import pandas as pd

from common import PROCESSED, ROOT, call_prompt, load_json_to_bq, preview_prompt

HOLDOUT = ROOT / "scripts" / "holdout_products.json"
OUT = ROOT / "api" / "app" / "data" / "backtest.json"
PANEL = "accessories"
MATCH = 0.75  # cosine similarity for a predicted complaint to count as matching a real one
INTERNAL = {"memories_claimed", "is_live", "original_preferred_language", "original_name"}


def describe(p: dict) -> str:
    """Amazon's 'about product' text, trimmed: the product as a shopper would see it."""
    text = " ".join(str(p.get("about_product") or p["product_name"]).split("|"))
    return text[:700]


def rating(v) -> float | None:
    try:
        r = float(v)
    except (TypeError, ValueError):
        return None
    return min(5.0, max(1.0, r))


async def predict(persona: dict, product: dict, category: str) -> dict | None:
    profile = {k: v for k, v in persona.items() if k not in INTERNAL}
    data, ok = await call_prompt(
        "p08_backtest", fallback=None, timeout_s=60,
        persona_json=json.dumps(profile, ensure_ascii=False), product_name=product["product_name"],
        product_description=describe(product), price_inr=int(product["price_inr"]), category=category,
    )
    r = rating(data.get("predicted_rating")) if ok and isinstance(data, dict) else None
    if r is None:
        return None
    return {"persona_id": persona["persona_id"], "segment_id": persona["segment_id"], "product_id": product["product_id"],
            "predicted_rating": r, "complaints": [str(c)[:160] for c in (data.get("predicted_complaints") or [])][:5],
            "review_text": str(data.get("review_text") or "")[:500]}


async def top_themes(per_item: list[list[str]], n: int) -> list[dict]:
    from app.services import themes

    groups = await themes.group(per_item)
    return groups[:n]


async def complaint_hits(real: list[dict], predicted: list[dict]) -> int:
    """How many real complaint themes have a semantically matching predicted theme."""
    from app.services.themes import _dot, _embed

    if not real or not predicted:
        return 0
    vr = await _embed([r["text"] for r in real])
    vp = await _embed([p["text"] for p in predicted])
    return sum(1 for a in vr if max(_dot(a, b) for b in vp) >= MATCH)


def score(rows: list[dict]) -> dict:
    """Adds calibrated_rating to each row (leave-one-out) and returns the metrics."""
    for r in rows:
        others = [o for o in rows if o is not r]
        offset = mean(o["actual_rating"] - o["predicted_rating"] for o in others)
        r["calibrated_rating"] = round(min(5.0, max(1.0, r["predicted_rating"] + offset)), 2)
    pairs = [(a, b) for i, a in enumerate(rows) for b in rows[i + 1:] if a["actual_rating"] != b["actual_rating"]]
    ordered = sum((a["predicted_rating"] - b["predicted_rating"]) * (a["actual_rating"] - b["actual_rating"]) > 0
                  for a, b in pairs)
    return {
        "mae_model": round(mean(abs(r["calibrated_rating"] - r["actual_rating"]) for r in rows), 3),
        "mae_raw": round(mean(abs(r["predicted_rating"] - r["actual_rating"]) for r in rows), 3),
        "mae_baseline": round(mean(abs(r["baseline_rating"] - r["actual_rating"]) for r in rows), 3),
        "bias": round(mean(r["predicted_rating"] - r["actual_rating"] for r in rows), 2),
        "correlation": round(correlation([r["predicted_rating"] for r in rows], [r["actual_rating"] for r in rows]), 2),
        "pairs_correct": ordered,
        "pairs_total": len(pairs),
        "complaint_hits": sum(r["complaint_hits"] for r in rows),
        "complaint_total": sum(r["complaint_total"] for r in rows),
    }


def rescore() -> None:
    data = json.loads(OUT.read_text(encoding="utf-8"))
    data["metrics"] = score(data["products"])
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data["metrics"], indent=2))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--personas", type=int, default=0, help="limit personas (0 = all in the panel)")
    ap.add_argument("--rescore", action="store_true", help="recompute metrics from backtest.json only")
    args = ap.parse_args()
    if args.rescore:
        rescore()
        return

    hold = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    category, products = hold["category"], hold["products"]
    personas = json.loads((PROCESSED / f"personas_{PANEL}.json").read_text(encoding="utf-8"))
    if args.personas:
        personas = personas[: args.personas]
    segments = {s["segment_id"]: s["share_percent"] / 100
                for s in json.loads((PROCESSED / f"segments_{PANEL}.json").read_text(encoding="utf-8"))}
    per_seg = Counter(p["segment_id"] for p in personas)
    weight = {p["persona_id"]: segments.get(p["segment_id"], 0) / per_seg[p["segment_id"]] for p in personas}

    reviews = pd.read_csv(PROCESSED / "reviews.csv")
    train = reviews[(reviews.panel == PANEL) & ~reviews.is_holdout].drop_duplicates("product_id")
    baseline = round(float(train.product_rating.mean()), 2)
    print(f"{len(personas)} personas x {len(products)} hidden products = {len(personas) * len(products)} calls; "
          f"baseline (avg rating of {len(train)} training products) = {baseline}")

    if args.dry_run:
        p = {k: v for k, v in personas[0].items() if k not in INTERNAL}
        print(preview_prompt("p08_backtest", persona_json=json.dumps(p, ensure_ascii=False)[:400] + "…",
                             product_name=products[0]["product_name"], product_description=describe(products[0]),
                             price_inr=int(products[0]["price_inr"]), category=category))
        return

    jobs = [predict(per, prod, category) for prod in products for per in personas]
    results = [r for r in await asyncio.gather(*jobs) if r]
    print(f"{len(results)} / {len(jobs)} predictions")

    real_signals = [json.loads(l) for l in (PROCESSED / "signals_holdout.jsonl").read_text(encoding="utf-8").splitlines()]
    real_by_product: dict[str, list[list[str]]] = defaultdict(list)
    for s in real_signals:
        real_by_product[s["product_id"]].append(s.get("complaints") or [])

    rows = []
    for prod in products:
        preds = [r for r in results if r["product_id"] == prod["product_id"]]
        if not preds:
            continue
        w = sum(weight[r["persona_id"]] for r in preds)
        predicted = round(sum(weight[r["persona_id"]] * r["predicted_rating"] for r in preds) / w, 2)
        real_c, pred_c = await asyncio.gather(top_themes(real_by_product[prod["product_id"]], 3),
                                              top_themes([r["complaints"] for r in preds], 5))
        hits = await complaint_hits(real_c, pred_c)
        rows.append({
            "product_id": prod["product_id"], "product_name": prod["product_name"][:90], "price_inr": prod["price_inr"],
            "actual_rating": prod["actual_rating"], "predicted_rating": predicted, "baseline_rating": baseline,
            "n_personas": len(preds), "predicted_complaints": pred_c, "actual_complaints": real_c,
            "complaint_hits": hits, "complaint_total": len(real_c),
        })
        print(f"  {prod['actual_rating']:.1f} real vs {predicted:.2f} predicted  hits {hits}/{len(real_c)}  {prod['product_name'][:60]}")

    metrics = score(rows)
    print(json.dumps(metrics, indent=2))

    run_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    from app.config import get_settings

    OUT.write_text(json.dumps({
        "label": "AI-simulated customers",
        "is_placeholder": False,
        "run_id": run_id,
        "run_at": now,
        "model": get_settings().gemini_flash_model,
        "category": "Electronics accessories",
        "n_holdout": len(rows),
        "n_personas": len(personas),
        "n_predictions": len(results),
        "baseline_description": f"Average rating of the {len(train)} products the personas were built from ({baseline}★)",
        "metrics": metrics,
        "products": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")

    load_json_to_bq("backtest_results", [
        {"run_id": run_id, "product_id": r["product_id"], "product_name": r["product_name"], "price_inr": r["price_inr"],
         "predicted_rating": r["predicted_rating"], "actual_rating": r["actual_rating"],
         "baseline_rating": r["baseline_rating"], "predicted_complaints": r["predicted_complaints"],
         "actual_complaints": r["actual_complaints"], "complaint_hits": r["complaint_hits"],
         "n_personas": r["n_personas"], "created_at": now}
        for r in rows
    ])


if __name__ == "__main__":
    asyncio.run(main())
