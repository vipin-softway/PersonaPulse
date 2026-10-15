"""Prompt 3: generate ~100 personas, one Gemini Pro call per segment, grounded in real reviews.

For each segment it sends the segment profile, its representative reviews
plus ~12 more matching reviews, the demographic mix, and a persona count
proportional to the segment's share. It then checks realism: memories must
be copied from the supplied reviews (invented ones are dropped), and it
reports age/skepticism spread. MAX_LIVE_PERSONAS personas, spread across
segments, are flagged is_live for live tests.

    python build_personas.py --dry-run           # show allocation + first prompt
    python build_personas.py --total 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

from common import PROCESSED, call_prompt, load_json_to_bq, preview_prompt

CATEGORY = "electronics accessories"
MARKET = "urban and semi-urban India"
DEMOGRAPHIC_MIX = "age 18-24: 30%, 25-34: 35%, 35-49: 25%, 50+: 10%; metro 50%, tier-2 35%, tier-3 15%"
EXTRA_REVIEWS = 12
MAX_REVIEW_CHARS = 600


def allocate(total: int, shares: dict[str, float], minimum: int = 1) -> dict[str, int]:
    """Largest-remainder split of `total` by share, at least `minimum` each."""
    raw = {k: total * v / sum(shares.values()) for k, v in shares.items()}
    alloc = {k: max(minimum, int(v)) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - int(raw[k]), reverse=True):
        if sum(alloc.values()) >= total:
            break
        alloc[k] += 1
    while sum(alloc.values()) > total:  # minimums can overshoot
        k = max(alloc, key=alloc.get)
        alloc[k] -= 1
    return alloc


def _words(items) -> set[str]:
    return {w for x in items or [] for w in re.findall(r"[a-z]{4,}", str(x).lower())}


def match_score(sig: dict, seg: dict) -> float:
    pri = len(set(sig.get("priorities") or []) & set(seg.get("top_priorities") or []))
    price = 1.0 if sig.get("price_sensitivity") and sig.get("price_sensitivity") == seg.get("price_sensitivity") else 0.0
    complaints = len(_words(sig.get("complaints")) & _words(seg.get("common_complaints")))
    return 2 * pri + price + 0.5 * complaints


def segment_reviews(seg: dict, signals: list[dict], text_of: dict[str, str], used: set[str]) -> list[dict]:
    """Representative reviews first, then the best-matching unused ones."""
    ids = [r for r in seg.get("representative_review_ids") or [] if r in text_of]
    ranked = sorted((s for s in signals if s["review_id"] in text_of and s["review_id"] not in used and s["review_id"] not in ids),
                    key=lambda s: match_score(s, seg), reverse=True)
    ids += [s["review_id"] for s in ranked[:EXTRA_REVIEWS]]
    used.update(ids)
    return [{"review_id": r, "review_text": text_of[r]} for r in ids]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def grounded(memories: list, review_texts: list[str]) -> list[str]:
    """Keep memories copied word for word from a supplied review (whole review or a 20+ char excerpt)."""
    texts = [_norm(t) for t in review_texts]
    return [m for m in memories or [] if isinstance(m, str) and len(_norm(m)) >= 20 and any(_norm(m) in t for t in texts)]


def pick_live(personas: list[dict], n: int, seed: int) -> None:
    by_seg: dict[str, list[dict]] = {}
    for p in personas:
        by_seg.setdefault(p["segment_id"], []).append(p)
    alloc = allocate(min(n, len(personas)), {k: len(v) for k, v in by_seg.items()})
    rng = random.Random(seed)
    for seg, group in by_seg.items():
        for p in rng.sample(group, alloc[seg]):
            p["is_live"] = True


CHUNK = 12  # personas per Gemini call: long JSON replies are more likely to be cut off


async def _generate(seg: dict, count: int, reviews: list[dict]) -> tuple[list[dict], bool]:
    data, ok = await call_prompt(
        "p03_personas", fallback={"personas": []}, timeout_s=600,
        category=CATEGORY, market=MARKET, segment_json=json.dumps(seg, ensure_ascii=False),
        representative_reviews_json=json.dumps(reviews, ensure_ascii=False), demographic_mix=DEMOGRAPHIC_MIX,
        count=count, segment_id=seg["segment_id"],
    )
    return [p for p in data.get("personas") or [] if isinstance(p, dict) and p.get("name")][:count], ok


async def build_segment(seg: dict, count: int, reviews: list[dict]) -> list[dict]:
    sizes = [CHUNK] * (count // CHUNK) + ([count % CHUNK] if count % CHUNK else [])
    results = await asyncio.gather(*(_generate(seg, n, reviews) for n in sizes))
    personas = [p for group, _ in results for p in group]
    texts = [r["review_text"] for r in reviews]
    out = []
    for i, p in enumerate(personas, start=1):
        p["persona_id"] = f"{seg['segment_id']}_p{i}"  # renumber across chunks
        p["segment_id"], p["segment_name"] = seg["segment_id"], seg["name"]
        p["memories_claimed"] = len(p.get("memories") or [])
        p["memories"] = grounded(p.get("memories"), texts)
        out.append(p)
    failed = sum(not ok for _, ok in results)
    print(f"  {seg['segment_id']} {seg['name']}: {len(out)}/{count} personas"
          f"{f'  ({failed} call(s) FAILED, rerun to fill the gap)' if failed else ''}")
    return out


def report(personas: list[dict]) -> None:
    claimed = sum(p["memories_claimed"] for p in personas)
    kept = sum(len(p["memories"]) for p in personas)
    ages = pd.Series([p.get("age") for p in personas if isinstance(p.get("age"), (int, float))])
    bands = pd.cut(ages, [0, 24, 34, 49, 120], labels=["18-24", "25-34", "35-49", "50+"]).value_counts(normalize=True)
    print("\nRealism check")
    print(f"  personas: {len(personas)}  live: {sum(bool(p.get('is_live')) for p in personas)}")
    print(f"  memories grounded in real reviews: {kept}/{claimed} ({100 * kept / max(claimed, 1):.0f}%)"
          f"; personas with <3 grounded memories: {sum(len(p['memories']) < 3 for p in personas)}")
    print("  age mix: " + ", ".join(f"{k} {v:.0%}" for k, v in bands.sort_index().items()))
    print("  skepticism: " + ", ".join(f"{k} {v}" for k, v in Counter(p.get("skepticism") for p in personas).most_common()))
    print("  city tier: " + ", ".join(f"{k} {v}" for k, v in Counter(p.get("city_tier") for p in personas).most_common()))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--live", type=int, default=int(os.environ.get("MAX_LIVE_PERSONAS", 30)))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-bq", action="store_true")
    args = ap.parse_args()

    segments = json.loads((PROCESSED / "segments.json").read_text(encoding="utf-8"))
    signals = [json.loads(l) for l in (PROCESSED / "signals.jsonl").read_text(encoding="utf-8").splitlines()]
    reviews = pd.read_csv(PROCESSED / "reviews.csv")
    reviews = reviews[~reviews.is_holdout]  # hidden back-test products never reach personas
    text_of = {r.review_id: (f"{r.review_title}. {r.review_content}" if isinstance(r.review_title, str) else r.review_content)[:MAX_REVIEW_CHARS]
               for r in reviews.itertuples(index=False)}

    counts = allocate(args.total, {s["segment_id"]: s["share_percent"] for s in segments}, minimum=3)
    used: set[str] = set()
    plan = [(s, counts[s["segment_id"]], segment_reviews(s, signals, text_of, used)) for s in segments]
    for s, n, revs in plan:
        print(f"  {s['segment_id']} {s['share_percent']:5.1f}% -> {n:3d} personas, {len(revs)} reviews  {s['name']}")

    if args.dry_run:
        s, n, revs = plan[0]
        print(preview_prompt("p03_personas", category=CATEGORY, market=MARKET, segment_json=json.dumps(s, ensure_ascii=False),
                             representative_reviews_json=json.dumps(revs[:2], ensure_ascii=False),
                             demographic_mix=DEMOGRAPHIC_MIX, count=n, segment_id=s["segment_id"]))
        return

    personas = [p for group in await asyncio.gather(*(build_segment(s, n, r) for s, n, r in plan)) for p in group]
    pick_live(personas, args.live, args.seed)
    report(personas)
    (PROCESSED / "personas.json").write_text(json.dumps(personas, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.no_bq:
        return
    from app.config import get_settings

    now, model = datetime.now(timezone.utc).isoformat(), get_settings().gemini_pro_model

    def num(v):
        return pd.to_numeric(v, errors="coerce") if v is not None else None

    rows = []
    for p in personas:
        profile = {k: v for k, v in p.items() if k not in ("memories_claimed", "is_live")}
        age, ceiling = num(p.get("age")), num(p.get("price_ceiling_inr"))
        rows.append({
            "persona_id": p["persona_id"], "segment_id": p["segment_id"], "segment_name": p["segment_name"],
            "name": p.get("name"), "age": None if pd.isna(age) else int(age), "gender": p.get("gender"),
            "city": p.get("city"), "city_tier": p.get("city_tier"), "occupation": p.get("occupation"),
            "monthly_income_band_inr": p.get("monthly_income_band_inr"),
            "price_ceiling_inr": None if pd.isna(ceiling) else float(ceiling),
            "skepticism": p.get("skepticism"), "preferred_language": p.get("preferred_language"),
            "profile": profile, "is_live": bool(p.get("is_live")), "model": model, "created_at": now,
        })
    load_json_to_bq("personas", rows)


if __name__ == "__main__":
    asyncio.run(main())
