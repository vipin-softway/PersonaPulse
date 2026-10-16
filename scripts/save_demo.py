"""Save a real test as the bundled demo (api/app/data/demo.json), loaded instantly by GET /demo.

    python save_demo.py <test_id>

Reads the test from BigQuery, marks it as a saved demo (no Gemini calls when
viewed), and writes the JSON the API serves. Rerun after a better test.
"""

from __future__ import annotations

import asyncio
import json
import sys

from common import ROOT

OUT = ROOT / "api" / "app" / "data" / "demo.json"


async def main(test_id: str) -> None:
    from app.services.tests_store import load_test

    result = await load_test(test_id)
    if result is None:
        raise SystemExit(f"Test {test_id} not found in BigQuery")
    if len(result["variants"]) < 2:
        print("Warning: the demo has no retested variant, so the comparison section will be empty.")
    for v in result["variants"]:
        if not v.get("insights"):
            print(f"Warning: variant {v['variant']} has no AI summary.")
        v.pop("insights_pending", None)
    run = result.get("run") or {}
    result.update(
        test_id="demo",
        source_test_id=test_id,
        is_demo=True,
        is_placeholder=False,
        run={**run, "mode": "saved_demo"},
    )
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    v = result["variants"]
    print(f"Saved {test_id} as demo: " + " -> ".join(
        f"{x['variant']} ₹{x['product']['price_inr']:.0f} {x['overall']['would_buy_pct']}% yes" for x in v))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
