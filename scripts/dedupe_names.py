"""Give live personas distinct names so quote cards don't repeat "Sneha" six times.

Within each panel's live personas: full names must be unique and no first name
or surname may appear more than twice. Replacement names are taken from non-live personas
of the same gender (so every name is still Gemini-generated). Rewrites
data/processed/personas_<panel>.json and reloads BigQuery personas.

    python dedupe_names.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

from common import PROCESSED, load_json_to_bq
from app.panels import PANELS

MAX_FIRST_NAME = 2
MAX_SURNAME = 2


def first(name: str) -> str:
    return name.split()[0] if name else ""


def last(name: str) -> str:
    return name.split()[-1] if name and len(name.split()) > 1 else ""


def dedupe(personas: list[dict], donors: list[dict]) -> int:
    live = [p for p in personas if p.get("is_live")]
    full_used: set[str] = set()
    first_used: Counter[str] = Counter()
    last_used: Counter[str] = Counter()

    def fits(name: str) -> bool:
        return (name not in full_used and first_used[first(name)] < MAX_FIRST_NAME
                and (not last(name) or last_used[last(name)] < MAX_SURNAME))

    def take(name: str) -> None:
        full_used.add(name)
        first_used[first(name)] += 1
        if last(name):
            last_used[last(name)] += 1

    changed = 0
    for p in live:
        name = p["name"]
        if fits(name):
            take(name)
            continue
        for d in donors:
            cand = d["name"]
            if d.get("gender") == p.get("gender") and fits(cand):
                p.setdefault("original_name", name)
                p["name"] = cand
                take(cand)
                changed += 1
                break
    return changed


def main() -> None:
    from build_personas import bq_rows
    from app.config import get_settings

    files = {p: PROCESSED / f"personas_{p}.json" for p in PANELS}
    data = {p: json.loads(f.read_text(encoding="utf-8")) for p, f in files.items()}
    all_non_live = [x for ps in data.values() for x in ps if not x.get("is_live")]
    for panel, ps in data.items():
        donors = [x for x in ps if not x.get("is_live")] + [x for x in all_non_live if x.get("panel") != panel]
        n = dedupe(ps, donors)
        live = [x for x in ps if x.get("is_live")]
        print(f"[{panel}] renamed {n}; live unique names {len({x['name'] for x in live})}/{len(live)}; "
              f"max first-name repeats {max(Counter(first(x['name']) for x in live).values())}, "
              f"max surname repeats {max(Counter(last(x['name']) for x in live if last(x['name'])).values())}")
        files[panel].write_text(json.dumps(ps, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = bq_rows([x for ps in data.values() for x in ps], get_settings().gemini_pro_model, datetime.now(timezone.utc).isoformat())
    load_json_to_bq("personas", rows)


if __name__ == "__main__":
    main()
