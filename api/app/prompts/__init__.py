"""Prompt templates copied verbatim from docs/prompts.md.

Each prompt N lives in `pNN_<name>.system.txt` and `pNN_<name>.user.txt`.
`render()` fills {{variable}} placeholders; it never edits prompt text.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).parent
_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@lru_cache
def _load(filename: str) -> str:
    return (_DIR / filename).read_text(encoding="utf-8")


def _fill(template: str, variables: dict[str, Any]) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in variables:
            raise KeyError(f"Missing prompt variable: {key}")
        v = variables[key]
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)

    return _VAR.sub(sub, template)


def render(name: str, **variables: Any) -> tuple[str, str]:
    """Return (system, user) for prompt `name`, e.g. render("p04_simulate", persona=...)."""
    return _fill(_load(f"{name}.system.txt"), variables), _fill(_load(f"{name}.user.txt"), variables)
