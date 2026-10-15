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
    {"segment_id": "seg_value", "name": "Value-hunting students", "share": 0.30},
    {"segment_id": "seg_health", "name": "Health-conscious professionals", "share": 0.22},
    {"segment_id": "seg_trend", "name": "Trend-driven Gen Z", "share": 0.20},
    {"segment_id": "seg_family", "name": "Practical family shoppers", "share": 0.16},
    {"segment_id": "seg_premium", "name": "Premium café lovers", "share": 0.12},
]

NAMES = ["Priya", "Arjun", "Meera", "Rahul", "Ananya", "Karthik", "Sneha", "Vikram", "Divya", "Rohan",
         "Lakshmi", "Aditya", "Pooja", "Siddharth", "Nisha", "Farhan", "Kavya", "Manish", "Ishita", "Suresh",
         "Neha", "Harish", "Tanvi", "Imran", "Revathi", "Gaurav", "Aisha", "Deepak", "Shreya", "Naveen"]
CITIES = ["Pune", "Bengaluru", "Chennai", "Mumbai", "Delhi", "Hyderabad", "Kochi", "Jaipur", "Indore", "Kolkata"]
AGES = {"seg_value": (18, 24), "seg_health": (27, 40), "seg_trend": (18, 26), "seg_family": (32, 48), "seg_premium": (25, 38)}

# (likes, objections, buyer quotes, non-buyer quotes) per segment, for each variant.
TEXT = {
    "original": {
        "seg_value": (["Cold coffee taste", "Convenient bottle"], ["Too expensive for a student", "Pack too big for one sitting"],
                      ["If it tastes like café cold coffee, ₹149 is still cheaper than a café."],
                      ["₹149 for one drink? I'd rather get two from the canteen.", "Nice idea, but that price is my whole lunch budget."]),
        "seg_health": (["Real coffee", "Less sugar than café drinks"], ["Looks like an energy drink", "Unclear sugar content"],
                       ["Fine as an occasional treat if the label is honest about sugar."],
                       ["The can design screams energy drink. I don't trust what's inside.", "I need to see grams of sugar before I buy."]),
        "seg_trend": (["Instagram-worthy idea", "Bold flavour"], ["Pack looks generic", "Too expensive to try"],
                      ["Would try it once if it shows up on Reels."],
                      ["Looks like every other energy drink, nothing to post about."]),
        "seg_family": (["Ready to drink", "Good for guests"], ["Too expensive per ml", "Looks like an energy drink"],
                       ["Handy to keep in the fridge for weekends."],
                       ["I wouldn't give my kids something that looks like an energy drink.", "Too costly to buy for the whole family."]),
        "seg_premium": (["Proper coffee strength", "Smooth texture"], ["Not as good as fresh brew"],
                        ["Good enough when I can't get to my café, and ₹149 is fair.", "I'd pay this for decent cold brew on the go."],
                        ["Bottled coffee never matches a fresh pour."]),
    },
    "v1": {
        "seg_value": (["₹99 is affordable", "Right size for one person", "Cold coffee taste"], ["Still want discounts"],
                      ["₹99 for a proper cold coffee? I'd buy it after class.", "Smaller pack, lower price, perfect for me."],
                      ["Would wait for a combo offer."]),
        "seg_health": (["Clean label", "Less sugar than café drinks", "Real coffee"], ["Want a no-sugar option"],
                       ["The new label makes it clear what's inside. I'd try it.", "Cleaner design looks like a coffee, not a stimulant."],
                       ["I'd still want a zero-sugar version."]),
        "seg_trend": (["Clean aesthetic", "Affordable to try"], ["Not unique enough"],
                      ["The new pack actually looks nice in a photo.", "At ₹99 I'll try it with friends."],
                      ["Cute pack, but I'm not sure it's special."]),
        "seg_family": (["Better value", "Looks like coffee now"], ["Small pack for sharing"],
                       ["At ₹99 I can pick a few for the fridge."],
                       ["Too small to share with the family."]),
        "seg_premium": (["Smooth texture", "Proper coffee strength"], ["Smaller pack feels less premium"],
                        ["Still good coffee. Price is fine."],
                        ["Smaller bottle feels like a downgrade.", "I'd rather pay more for a bigger bottle."]),
    },
}

# Probability of would_buy per segment per variant: tells the demo story.
P_BUY = {
    "original": {"seg_value": 0.12, "seg_health": 0.29, "seg_trend": 0.34, "seg_family": 0.40, "seg_premium": 0.67},
    "v1": {"seg_value": 0.78, "seg_health": 0.58, "seg_trend": 0.50, "seg_family": 0.60, "seg_premium": 0.34},
}
WTP_MEAN = {"seg_value": 85, "seg_health": 120, "seg_trend": 105, "seg_family": 110, "seg_premium": 165}

PRODUCTS = {
    "original": {"name": "BrewChill Cold Coffee", "description": "Ready-to-drink cold coffee made with Arabica, in a slim 300 ml can.",
                 "price_inr": 149, "pack_size": "300 ml can", "channel": "Quick commerce"},
    "v1": {"name": "BrewChill Cold Coffee (Mini)", "description": "Same Arabica cold coffee in a 200 ml bottle with a clean, café-style label showing sugar per serving.",
           "price_inr": 99, "pack_size": "200 ml bottle", "channel": "Quick commerce"},
}


COUNTS = {"seg_value": 9, "seg_health": 7, "seg_trend": 6, "seg_family": 5, "seg_premium": 3}  # 30 live personas


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
        "headline": "Only 3 in 10 AI customers would buy at ₹149, held back by price and an energy-drink look.",
        "overall_verdict": "launch_with_changes",
        "best_segments": [
            {"segment_name": "Premium café lovers", "why": "They value proper coffee strength and see ₹149 as fair for cold brew on the go."},
            {"segment_name": "Practical family shoppers", "why": "Like having a ready-to-drink option in the fridge for weekends and guests."},
        ],
        "weakest_segments": [
            {"segment_name": "Value-hunting students", "why": "The largest segment, but ₹149 is far above what they expect to pay for one drink."},
            {"segment_name": "Health-conscious professionals", "why": "The can reads as an energy drink and the sugar content is unclear."},
        ],
        "price_insight": "Median willingness to pay is ₹102, and only 10% would pay ₹149 or more. A price near ₹99 would clear most customers' ceiling.",
        "top_3_objections": [
            {"objection": "Too expensive for one drink", "segments_affected": ["Value-hunting students", "Practical family shoppers"]},
            {"objection": "Looks like an energy drink", "segments_affected": ["Health-conscious professionals", "Practical family shoppers"]},
            {"objection": "Pack looks generic", "segments_affected": ["Trend-driven Gen Z"]},
        ],
        "top_3_strengths": ["Cold coffee taste", "Convenient ready-to-drink format", "Less sugar than café drinks"],
        "standout_quotes": ["₹149 for one drink? I'd rather get two from the canteen."],
        "recommended_target_segment": "Value-hunting students, if the price comes down",
        "caveat": "These are AI-simulated customers; validate the winning variant with a small real-customer test.",
    }
    improved["insights"] = {
        "headline": "The ₹99 mini pack doubles purchase intent to 60%, led by students.",
        "overall_verdict": "launch",
        "best_segments": [
            {"segment_name": "Value-hunting students", "why": "₹99 fits their budget and the 200 ml size suits a single serving."},
            {"segment_name": "Health-conscious professionals", "why": "The clean label showing sugar per serving removed the energy-drink concern."},
        ],
        "weakest_segments": [
            {"segment_name": "Premium café lovers", "why": "The smaller bottle feels less premium to them."},
        ],
        "price_insight": "Two thirds of AI customers would pay ₹99 or more, with a median of ₹110, so there is a little headroom.",
        "top_3_objections": [
            {"objection": "Smaller pack feels less premium", "segments_affected": ["Premium café lovers"]},
            {"objection": "Too small to share", "segments_affected": ["Practical family shoppers"]},
            {"objection": "Want a no-sugar option", "segments_affected": ["Health-conscious professionals"]},
        ],
        "top_3_strengths": ["Affordable price", "Right size for one person", "Clean, café-style label"],
        "standout_quotes": ["₹99 for a proper cold coffee? I'd buy it after class."],
        "recommended_target_segment": "Value-hunting students",
        "caveat": "These are AI-simulated customers; validate with a small real-customer test before scaling.",
    }
    suggestions = [
        {"variant_id": "v1", "title": "Smaller pack at ₹99 with a café-style label",
         "changes": ["Price ₹149 → ₹99", "300 ml can → 200 ml bottle", "Clean label showing sugar per serving"],
         "objections_addressed": ["Too expensive for one drink", "Looks like an energy drink"],
         "expected_effect": "Students and health-conscious buyers should respond better: lower price and a coffee-like look.",
         "risk": "Premium café lovers may see the smaller bottle as less premium.",
         "updated_product": {"product_name": PRODUCTS["v1"]["name"], "product_description": PRODUCTS["v1"]["description"],
                             "price_inr": 99, "pack_size": "200 ml bottle", "channel": "Quick commerce"},
         "imagen_prompt": "Clean product packshot of a slim 200 ml glass cold coffee bottle, cream and coffee-brown label, sugar per serving shown, soft daylight, white background."},
        {"variant_id": "v2", "title": "Student 2-pack for ₹249",
         "changes": ["2 × 300 ml cans for ₹249", "Campus-focused messaging"],
         "objections_addressed": ["Too expensive for one drink"],
         "expected_effect": "Lowers the per-drink price for students while keeping the premium can.",
         "risk": "Still looks like an energy drink to health-conscious buyers.",
         "updated_product": {"product_name": "BrewChill Cold Coffee 2-pack", "product_description": PRODUCTS["original"]["description"],
                             "price_inr": 249, "pack_size": "2 × 300 ml cans", "channel": "Quick commerce"},
         "imagen_prompt": None},
    ]
    return build_test_result("demo", [original, improved], created_at="2026-10-17T19:30:00Z",
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
