"""Clean the Kaggle "Amazon Sales Dataset" CSV and load one review per row into BigQuery.

Each CSV row is one product with up to 8 reviews packed into comma-joined
cells (review_id, review_title, review_content). We split them back into
individual reviews, keep one category pool (electronics accessories), hide
N products for the back-test, and drop reviewer names/IDs (not needed, PII).

    python load_reviews.py --dry-run     # clean + pick hold-outs, write files only
    python load_reviews.py               # ...and load into BigQuery reviews_raw

Outputs:
    data/processed/reviews.csv           cleaned reviews (git-ignored)
    scripts/holdout_products.json        hidden back-test products (committed)
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

import pandas as pd

from common import ROOT

RAW = ROOT / "data" / "raw" / "amazon.csv"
PROCESSED = ROOT / "data" / "processed" / "reviews.csv"
HOLDOUT_FILE = ROOT / "scripts" / "holdout_products.json"

CATEGORY_NAME = "electronics accessories"
# (level-1, level-2) category pairs in the pool, minus leaves that are not accessories.
POOL = {
    ("Computers&Accessories", "Accessories&Peripherals"),
    ("Electronics", "Mobiles&Accessories"),
    ("Electronics", "Headphones,Earbuds&Accessories"),
}
EXCLUDE_LEAVES = {"Smartphones", "BasicMobiles"}

# Reviews are joined with "," and no space; commas inside a review are usually followed by a space.
JOIN = re.compile(r",(?! )")


def inr(s) -> float | None:
    v = pd.to_numeric(str(s).replace("₹", "").replace(",", "").strip(), errors="coerce")
    return None if pd.isna(v) else float(v)


def split_reviews(text: str, n: int) -> list[str] | None:
    """Split a packed cell into exactly n reviews, or None if it can't be done reliably."""
    parts = JOIN.split(str(text))
    i = 1
    while len(parts) > n and i < len(parts):
        # A piece that doesn't start with a capital letter is most likely a continuation.
        if not parts[i][:1].isupper():
            parts[i - 1] += "," + parts.pop(i)
        else:
            i += 1
    return [p.strip() for p in parts] if len(parts) == n else None


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"csv_rows": len(df)}
    levels = df["category"].str.split("|")
    df = df[[(l[0], l[1]) in POOL and l[-1] not in EXCLUDE_LEAVES for l in levels]]
    df = df.drop_duplicates("product_id")
    stats["pool_products"] = len(df)

    rows, skipped = [], 0
    for p in df.itertuples(index=False):
        ids = str(p.review_id).split(",")
        titles = split_reviews(p.review_title, len(ids)) or [""] * len(ids)
        contents = split_reviews(p.review_content, len(ids))
        if contents is None:
            skipped += 1
            continue
        rating = pd.to_numeric(p.rating, errors="coerce")
        count = pd.to_numeric(str(p.rating_count).replace(",", ""), errors="coerce")
        for rid, title, content in zip(ids, titles, contents):
            if len(content) < 15:  # "Good", "Nice product" carry no decision signal
                continue
            rows.append({
                "review_id": rid.strip(),
                "product_id": p.product_id,
                "product_name": str(p.product_name)[:200],
                "category": str(p.category).split("|")[-1],
                "price_inr": inr(p.discounted_price),
                "list_price_inr": inr(p.actual_price),
                "product_rating": None if pd.isna(rating) else float(rating),
                "rating_count": None if pd.isna(count) else int(count),
                "about_product": str(p.about_product)[:1500],
                "review_title": title[:200],
                "review_content": content[:2000],
            })
    out = pd.DataFrame(rows).drop_duplicates("review_id")
    stats.update(products_skipped_unsplittable=skipped, reviews=len(out), products_with_reviews=out.product_id.nunique())
    return out, stats


def pick_holdouts(reviews: pd.DataFrame, n: int, seed: int) -> list[dict]:
    """Hide n well-rated-count products spread across the rating range, so the back-test isn't trivial."""
    products = (
        reviews.groupby("product_id")
        .agg(product_name=("product_name", "first"), category=("category", "first"), price_inr=("price_inr", "first"),
             product_rating=("product_rating", "first"), rating_count=("rating_count", "first"),
             about_product=("about_product", "first"))
        .reset_index()
    )
    products = products[(products.rating_count >= 500) & products.product_rating.notna() & products.price_inr.notna()]
    # One product per rating band (quantiles), so low- and high-rated products are both represented.
    products["band"] = pd.qcut(products.product_rating.rank(method="first"), q=n, labels=False)
    picked = products.groupby("band").sample(n=1, random_state=seed).sort_values("product_rating")
    return [
        {"product_id": r.product_id, "product_name": r.product_name, "category": r.category, "price_inr": r.price_inr,
         "actual_rating": r.product_rating, "rating_count": int(r.rating_count), "about_product": r.about_product}
        for r in picked.itertuples(index=False)
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(RAW))
    ap.add_argument("--holdout", type=int, default=10, help="products hidden for the back-test")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true", help="write local files only; skip BigQuery")
    args = ap.parse_args()

    reviews, stats = clean(pd.read_csv(args.csv))
    holdouts = pick_holdouts(reviews, args.holdout, args.seed)
    hidden = {h["product_id"] for h in holdouts}
    reviews["is_holdout"] = reviews.product_id.isin(hidden)
    reviews["loaded_at"] = datetime.now(timezone.utc).isoformat()
    reviews["rating_count"] = reviews["rating_count"].astype("Int64")  # NaN made it float; BigQuery wants INT64
    stats.update(holdout_products=len(hidden), holdout_reviews=int(reviews.is_holdout.sum()),
                 training_reviews=int((~reviews.is_holdout).sum()))

    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    reviews.to_csv(PROCESSED, index=False)
    HOLDOUT_FILE.write_text(json.dumps({"category": CATEGORY_NAME, "products": holdouts}, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(f"Wrote {PROCESSED.relative_to(ROOT)} and {HOLDOUT_FILE.relative_to(ROOT)}")
    for h in holdouts:
        print(f"  hidden: {h['actual_rating']:.1f}★  ₹{h['price_inr']:.0f}  {h['product_name'][:70]}")

    if args.dry_run:
        return

    from common import load_json_to_bq

    load_json_to_bq("reviews_raw", json.loads(reviews.to_json(orient="records")))


if __name__ == "__main__":
    main()
