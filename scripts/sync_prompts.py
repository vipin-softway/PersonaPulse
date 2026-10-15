"""Copy prompt text verbatim from docs/prompts.md into api/app/prompts/.

docs/prompts.md is the source of truth. Each "## Prompt N: ..." section has a
fenced ```text block after "System instruction:" and another after
"User prompt:". This script writes them unchanged to
api/app/prompts/pNN_<name>.system.txt and .user.txt.

    python3 scripts/sync_prompts.py          # write files
    python3 scripts/sync_prompts.py --check  # exit 1 if files are out of date
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "prompts.md"
OUT = ROOT / "api" / "app" / "prompts"

NAMES = {
    1: "p01_signals",
    2: "p02_segments",
    3: "p03_personas",
    4: "p04_simulate",
    5: "p05_focus_group",
    6: "p06_insights",
    7: "p07_improve",
    8: "p08_backtest",
}

SECTION = re.compile(r"^## Prompt (\d+):.*?$(.*?)(?=^## |\Z)", re.M | re.S)
BLOCK = re.compile(r"^(System instruction|User prompt):\s*\n+```text\n(.*?)\n```", re.M | re.S)


def extract() -> dict[str, str]:
    files: dict[str, str] = {}
    for m in SECTION.finditer(SRC.read_text(encoding="utf-8")):
        n, body = int(m.group(1)), m.group(2)
        blocks = {kind: text for kind, text in BLOCK.findall(body)}
        if set(blocks) != {"System instruction", "User prompt"}:
            raise SystemExit(f"Prompt {n}: expected one System instruction and one User prompt block")
        files[f"{NAMES[n]}.system.txt"] = blocks["System instruction"] + "\n"
        files[f"{NAMES[n]}.user.txt"] = blocks["User prompt"] + "\n"
    if len(files) != 2 * len(NAMES):
        raise SystemExit(f"Expected {len(NAMES)} prompts, found {len(files) // 2}")
    return files


def main() -> None:
    files = extract()
    stale = [name for name, text in files.items() if not (OUT / name).exists() or (OUT / name).read_text(encoding="utf-8") != text]
    if "--check" in sys.argv:
        if stale:
            raise SystemExit(f"Out of date: {', '.join(stale)}. Run scripts/sync_prompts.py")
        print("Prompt files match docs/prompts.md")
        return
    for name in stale:
        (OUT / name).write_text(files[name], encoding="utf-8")
    print(f"Wrote {len(stale)} file(s); {len(files) - len(stale)} already up to date.")


if __name__ == "__main__":
    main()
