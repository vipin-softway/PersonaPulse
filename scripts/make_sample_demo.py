"""Generate PLACEHOLDER demo + back-test JSON bundled with the API.

These files let the UI and the /demo and /backtest endpoints work before any
Gemini run. They are flagged `is_placeholder: true` and the UI says so.
Replace them with real results in Phase 4 (demo) and Phase 5 (back-test).

Run from the repo root:  python3 scripts/make_sample_demo.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.services.aggregate import aggregate_variant, build_test_result  # noqa: E402

OUT_DIR = ROOT / "api" / "app" / "data"
rng = random.Random(42)

SEGMENTS = [
    {"segment_id": "seg_value", "name": "Value-for-money buyers", "share": 0.30},
    {"segment_id": "seg_durable", "name": "Durability skeptics", "share": 0.22},
    {"segment_id": "seg_power", "name": "Fast-charging power users", "share": 0.20},
    {"segment_id": "seg_brand", "name": "Brand-trust shoppers", "share": 0.16},
    {"segment_id": "seg_gift", "name": "Convenience & gift buyers", "share": 0.12},
]

NAMES = ["Priya", "Arjun", "Meera", "Rahul", "Ananya", "Karthik", "Sneha", "Vikram", "Divya", "Rohan",
         "Lakshmi", "Aditya", "Pooja", "Siddharth", "Nisha", "Farhan", "Kavya", "Manish", "Ishita", "Suresh",
         "Neha", "Harish", "Tanvi", "Imran", "Revathi", "Gaurav", "Aisha", "Deepak", "Shreya", "Naveen"]
CITIES = ["Pune", "Bengaluru", "Chennai", "Mumbai", "Delhi", "Hyderabad", "Kochi", "Jaipur", "Indore", "Kolkata"]
AGES = {"seg_value": (18, 26), "seg_durable": (26, 45), "seg_power": (22, 35), "seg_brand": (30, 52), "seg_gift": (24, 40)}

# (likes, objections, buyer quotes, non-buyer quotes) per segment, for each variant.
TEXT = {
    "original": {
        "seg_value": (["Braided build", "Long 2 m length"], ["Too expensive for a cable", "Cheaper cables do the same job"],
                      ["If it really lasts two years, ₹799 works out cheaper than buying three ₹299 cables."],
                      ["₹799 for a cable? My ₹299 one charges just fine.", "Nice cable, but I'd wait for a sale under ₹400."]),
        "seg_durable": (["Nylon braiding", "Bend-tested claim"], ["No warranty mentioned", "Braided cables still fray at the neck"],
                        ["The bend test sounds serious. I'll try it."],
                        ["Every braided cable I bought frayed at the connector within months. No warranty, no deal.",
                         "10,000 bends is just a claim. Show me a replacement warranty."]),
        "seg_power": (["65W laptop charging", "One cable for phone and laptop"], ["Want e-marker chip details"],
                      ["65W on a 2 m cable means I can charge my laptop from the sofa. Worth ₹799.",
                       "Finally one cable for my phone and MacBook. Buying."],
                      ["Need to know if it has an e-marker chip before trusting 65W."]),
        "seg_brand": (["Looks premium"], ["Unknown brand", "No reviews yet"],
                      ["Looks well made, I'll take a chance."],
                      ["Never heard of this brand. I'll stick with what I know for ₹100 more.", "Zero reviews, so I'll wait."]),
        "seg_gift": (["Premium look", "Long cable"], ["Plain packaging"],
                     ["Good as a small gift for my brother, it looks premium.", "2 m is great next to the bed."],
                     ["Packaging is too plain to gift."]),
    },
    "v1": {
        "seg_value": (["₹449 is fair", "Braided build", "Warranty included"], ["Still want a 2-pack deal"],
                      ["₹449 with 18 months' warranty? That's an easy yes.", "At this price it beats my usual ₹299 cable."],
                      ["I'd wait for a 2-pack offer."]),
        "seg_durable": (["18-month replacement warranty", "Bend-test shown on pack"], ["Want to see real reviews"],
                        ["If it frays they'll replace it, so I'm not taking a risk.", "Warranty on the box finally makes the claim believable."],
                        ["Warranty is good, but I'll wait for a few reviews."]),
        "seg_power": (["65W laptop charging", "Good price"], ["Doubt 65W at this price"],
                      ["Same 65W cable, cheaper. Buying two."],
                      ["At ₹449 I'm not sure it really does 65W safely.", "Cheaper makes me doubt the chip inside."]),
        "seg_brand": (["Warranty builds trust"], ["Unknown brand"],
                      ["A replacement warranty makes an unknown brand less risky."],
                      ["Still an unknown brand, warranty or not."]),
        "seg_gift": (["Affordable gift", "Clean box"], ["Plain packaging"],
                     ["At ₹449 it's an easy add-on gift.", "Good value for a stocking filler."],
                     ["Still a bit plain to gift."]),
    },
}

# Probability of a "yes" per segment per variant: tells the demo story.
P_BUY = {
    "original": {"seg_value": 0.11, "seg_durable": 0.14, "seg_power": 0.67, "seg_brand": 0.20, "seg_gift": 0.67},
    "v1": {"seg_value": 0.78, "seg_durable": 0.71, "seg_power": 0.50, "seg_brand": 0.40, "seg_gift": 0.67},
}
WTP_MEAN = {"seg_value": 380, "seg_durable": 520, "seg_power": 820, "seg_brand": 600, "seg_gift": 650}

PRODUCTS = {
    "original": {"name": "WeaveCharge 65W USB-C Cable", "description": "Nylon-braided USB-C to USB-C cable, 2 m, 65W fast charging for phones and laptops, 10,000-bend tested.",
                 "price_inr": 799, "pack_size": "1 cable, 2 m", "channel": "E-commerce marketplace"},
    "v1": {"name": "WeaveCharge 65W USB-C Cable", "description": "Same 2 m braided 65W cable, now with an 18-month replacement warranty and the bend test shown on the box.",
           "price_inr": 449, "pack_size": "1 cable, 2 m", "channel": "E-commerce marketplace"},
}


COUNTS = {"seg_value": 9, "seg_durable": 7, "seg_power": 6, "seg_brand": 5, "seg_gift": 3}  # 30 live personas

def personas() -> list[dict]:
    out, i = [], 0
    for s in SEGMENTS:
        for _ in range(COUNTS[s["segment_id"]]):
            lo, hi = AGES[s["segment_id"]]
            out.append({"persona_id": f"p{i:03d}", "persona_name": NAMES[i % len(NAMES)], "age": rng.randint(lo, hi),
                        "city": rng.choice(CITIES), "segment_id": s["segment_id"], "segment_name": s["name"]})
            i += 1
    return out


def rows_for(variant: str, people: list[dict]) -> list[dict]:
    # Exactly round(n * p) buyers per segment so the story is stable.
    buyers: set[str] = set()
    for seg, n in COUNTS.items():
        ids = [p["persona_id"] for p in people if p["segment_id"] == seg]
        buyers.update(rng.sample(ids, k=round(n * P_BUY[variant][seg])))
    rows = []
    for p in people:
        seg = p["segment_id"]
        likes, objections, yes_q, no_q = TEXT[variant][seg]
        buy = p["persona_id"] in buyers
        intent = rng.randint(4, 5) if buy else rng.randint(1, 3)
        wtp = max(40, round(rng.gauss(WTP_MEAN[seg] * (0.95 if variant == "v1" else 1), 18) / 5) * 5)
        decision = "yes" if buy else ("maybe" if intent == 3 else "no")
        rows.append({**p, "variant": variant, "would_buy": decision, "purchase_intent": intent,
                     "willingness_to_pay_inr": wtp,
                     "top_likes": rng.sample(likes, k=min(2, len(likes))),
                     "top_objections": rng.sample(objections, k=1) if (not buy or rng.random() < 0.3) else [],
                     "main_reason": (likes if buy else objections)[0],
                     "quote": rng.choice(yes_q if buy else no_q)})
    return rows


def demo() -> dict:
    people = personas()
    original = aggregate_variant("original", PRODUCTS["original"], rows_for("original", people), SEGMENTS)
    improved = aggregate_variant("v1", PRODUCTS["v1"], rows_for("v1", people), SEGMENTS)
    original["insights"] = {
        "headline": "Only 3 in 10 AI customers would buy at ₹799: price and durability doubts hold back the biggest segments.",
        "overall_verdict": "launch_with_changes",
        "best_segments": [
            {"segment_name": "Fast-charging power users", "why": "65W laptop charging on a 2 m cable solves a real problem for them, and ₹799 feels fair."},
            {"segment_name": "Convenience & gift buyers", "why": "The premium look and long cable appeal; price matters less for an occasional purchase."},
        ],
        "weakest_segments": [
            {"segment_name": "Value-for-money buyers", "why": "The largest segment, but they compare against ₹299 cables that already work."},
            {"segment_name": "Durability skeptics", "why": "Past braided cables frayed at the connector, and there is no warranty to back the bend-test claim."},
        ],
        "price_insight": "Median willingness to pay is well below ₹799, and only power users regularly go above it. A price under ₹500 would clear most customers' ceiling.",
        "top_3_objections": [
            {"objection": "Too expensive for a cable", "segments_affected": ["Value-for-money buyers"]},
            {"objection": "No warranty mentioned", "segments_affected": ["Durability skeptics", "Brand-trust shoppers"]},
            {"objection": "Unknown brand with no reviews", "segments_affected": ["Brand-trust shoppers"]},
        ],
        "top_3_strengths": ["65W laptop charging", "Braided build", "Long 2 m length"],
        "standout_quotes": ["Every braided cable I bought frayed at the connector within months. No warranty, no deal."],
        "recommended_target_segment": "Value-for-money buyers, if the price drops and a warranty is added",
        "caveat": "These are AI-simulated customers; validate the winning variant with a small real-customer test.",
    }
    improved["insights"] = {
        "headline": "At ₹449 with an 18-month warranty, purchase intent doubles to over 60%, led by value buyers and durability skeptics.",
        "overall_verdict": "launch",
        "best_segments": [
            {"segment_name": "Value-for-money buyers", "why": "₹449 now beats replacing cheap cables, and the warranty removes the risk."},
            {"segment_name": "Durability skeptics", "why": "A replacement warranty on the box makes the bend-test claim believable."},
        ],
        "weakest_segments": [
            {"segment_name": "Brand-trust shoppers", "why": "Still wary of an unknown brand, though the warranty helps."},
            {"segment_name": "Fast-charging power users", "why": "Some now doubt a ₹449 cable can safely deliver 65W."},
        ],
        "price_insight": "Most AI customers would pay ₹449 or more, so the new price sits comfortably inside their range.",
        "top_3_objections": [
            {"objection": "Doubt 65W at this price", "segments_affected": ["Fast-charging power users"]},
            {"objection": "Unknown brand", "segments_affected": ["Brand-trust shoppers"]},
            {"objection": "Want to see real reviews first", "segments_affected": ["Durability skeptics"]},
        ],
        "top_3_strengths": ["Fair price", "18-month replacement warranty", "Braided 65W build"],
        "standout_quotes": ["If it frays they'll replace it, so I'm not taking a risk."],
        "recommended_target_segment": "Value-for-money buyers",
        "caveat": "These are AI-simulated customers; validate with a small real-customer test before scaling.",
    }
    suggestions = [
        {"variant_id": "v1", "title": "₹449 with an 18-month replacement warranty",
         "changes": ["Price ₹799 → ₹449", "Add an 18-month replacement warranty", "Show the bend test on the box"],
         "objections_addressed": ["Too expensive for a cable", "No warranty mentioned"],
         "expected_effect": "Value buyers and durability skeptics should respond better: lower price and lower risk.",
         "risk": "Power users may doubt a cheaper cable delivers 65W safely.",
         "updated_product": {"product_name": PRODUCTS["v1"]["name"], "product_description": PRODUCTS["v1"]["description"],
                             "price_inr": 449, "pack_size": "1 cable, 2 m", "channel": "E-commerce marketplace"},
         "imagen_prompt": "Clean product packshot of a coiled grey nylon-braided USB-C cable on a matte white box showing an 18-month warranty badge and a bend-test icon, soft studio light, white background."},
        {"variant_id": "v2", "title": "Bundle with a 20W adapter for ₹999",
         "changes": ["Add a 20W USB-C wall adapter", "Price ₹799 → ₹999 for the bundle"],
         "objections_addressed": ["Too expensive for a cable"],
         "expected_effect": "Gift buyers and first-time USB-C users get a complete kit, so the price feels justified.",
         "risk": "Value buyers who already own an adapter will see it as a more expensive cable.",
         "updated_product": {"product_name": "WeaveCharge 65W USB-C Cable + 20W Adapter", "product_description": "2 m braided 65W USB-C cable bundled with a 20W USB-C wall adapter.",
                             "price_inr": 999, "pack_size": "1 cable + 1 adapter", "channel": "E-commerce marketplace"},
         "imagen_prompt": None},
    ]
    return build_test_result("demo", [original, improved], created_at="2026-10-17T19:30:00Z", panel="accessories",
                             is_demo=True, is_placeholder=True, suggestions=suggestions)


def correlation(xs: list[float], ys: list[float]) -> float:
    from statistics import correlation as pearson

    return pearson(xs, ys)


def backtest() -> dict:
    products = [
        ("USB-C fast charger 20W", 499, 4.2), ("Braided Lightning cable 1m", 299, 4.0), ("Wireless earbuds (budget)", 999, 3.6),
        ("Laptop stand aluminium", 1299, 4.3), ("Power bank 10000mAh", 899, 4.1), ("Smartwatch strap silicone", 199, 3.8),
        ("Bluetooth speaker mini", 1499, 3.9), ("HDMI cable 2m", 349, 4.2), ("Wired mouse ergonomic", 449, 4.0),
        ("Phone tripod with remote", 699, 3.5),
    ]
    brng = random.Random(7)  # independent of the demo's random stream
    baseline = 4.0  # category average rating of the products personas were built from
    rows = []
    for i, (name, price, actual) in enumerate(products):
        predicted = round(min(5, max(1, actual + brng.gauss(0, 0.16))), 2)
        rows.append({"product_id": f"h{i:02d}", "product_name": name, "price_inr": price,
                     "actual_rating": actual, "predicted_rating": predicted, "baseline_rating": baseline})
    mae = lambda key: round(sum(abs(r[key] - r["actual_rating"]) for r in rows) / len(rows), 3)  # noqa: E731
    return {
        "label": "AI-simulated customers",
        "is_placeholder": True,
        "category": "Electronics accessories",
        "n_holdout": len(rows),
        "baseline_description": "Category average rating of the products the personas were built from",
        "metrics": {"mae_model": mae("predicted_rating"), "mae_baseline": mae("baseline_rating"),
                    "correlation": round(correlation([r["predicted_rating"] for r in rows], [r["actual_rating"] for r in rows]), 2)},
        "products": rows,
    }


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "demo.json").write_text(json.dumps(demo(), ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "backtest_sample.json").write_text(json.dumps(backtest(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'demo.json'} and {OUT_DIR / 'backtest_sample.json'}")
