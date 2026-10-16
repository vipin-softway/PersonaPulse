"""Group free-text likes/objections into themes with Vertex AI text embeddings.

Each AI customer phrases things differently ("price is double my ₹400 limit",
"too expensive for a cable"), so exact-text counting finds no patterns.
Phrases are embedded, clustered by cosine similarity, and each theme is
counted once per customer and labelled with its most central short phrase.
No prompt is involved. If embeddings fail, exact-text counting is used.
"""

from __future__ import annotations

import logging
import math
from collections import Counter

from google.genai import types

from functools import lru_cache

from google import genai

from app.config import get_settings

log = logging.getLogger("personapulse.themes")

EMBED_MODEL = "text-embedding-005"  # one vector per input text; batch of up to 250
EMBED_LOCATION = "us-central1"  # consistently ~3 s; the global endpoint's first call can take 10 s+
DIMS = 256
THRESHOLD = 0.66  # cosine similarity to join a theme (tuned on a live test: distinct, non-overlapping themes)
TOP_N = 6


@lru_cache
def _client() -> genai.Client:
    return genai.Client(vertexai=True, project=get_settings().gcp_project, location=EMBED_LOCATION)


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


async def _embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), 100):
        resp = await _client().aio.models.embed_content(
            model=EMBED_MODEL, contents=texts[i : i + 100],
            config=types.EmbedContentConfig(task_type="CLUSTERING", output_dimensionality=DIMS))
        out += [_unit(list(e.values)) for e in resp.embeddings]
    if len(out) != len(texts):
        raise ValueError(f"expected {len(texts)} embeddings, got {len(out)}")
    return out


def _exact(per_persona: list[list[str]], n: int) -> list[dict]:
    counts: Counter[str] = Counter()
    for items in per_persona:
        counts.update({t for t in items})
    return [{"text": t, "count": c, "pct": round(100 * c / n, 1) if n else 0.0} for t, c in counts.most_common(TOP_N)]


def cluster(phrases: list[str], vectors: list[list[float]]) -> list[list[int]]:
    """Greedy centroid clustering; short phrases first so they seed readable themes."""
    order = sorted(range(len(phrases)), key=lambda i: len(phrases[i]))
    clusters: list[list[int]] = []
    centroids: list[list[float]] = []
    for i in order:
        best, best_sim = -1, THRESHOLD
        for c, cen in enumerate(centroids):
            sim = _dot(vectors[i], cen)
            if sim >= best_sim:
                best, best_sim = c, sim
        if best < 0:
            clusters.append([i])
            centroids.append(vectors[i])
        else:
            clusters[best].append(i)
            members = clusters[best]
            centroids[best] = _unit([sum(vectors[m][d] for m in members) / len(members) for d in range(DIMS)])
    return clusters


def _label(members: list[int], phrases: list[str], vectors: list[list[float]]) -> str:
    cen = _unit([sum(vectors[m][d] for m in members) for d in range(DIMS)])
    closest = sorted(members, key=lambda m: -_dot(vectors[m], cen))[:3]
    return min((phrases[m] for m in closest), key=len)


async def group(per_persona: list[list[str]]) -> list[dict]:
    """per_persona: each customer's phrases. Returns [{text, count, pct}] top themes."""
    n = len(per_persona)
    phrases = sorted({p for items in per_persona for p in items})
    if len(phrases) < 2:
        return _exact(per_persona, n)
    try:
        vectors = await _embed(phrases)
    except Exception:  # noqa: BLE001
        log.exception("Embedding themes failed; using exact text")
        return _exact(per_persona, n)
    index = {p: i for i, p in enumerate(phrases)}
    themes = []
    for members in cluster(phrases, vectors):
        member_set = set(members)
        count = sum(1 for items in per_persona if any(index[p] in member_set for p in items))
        themes.append({"text": _label(members, phrases, vectors), "count": count,
                       "pct": round(100 * count / n, 1) if n else 0.0})
    themes.sort(key=lambda t: (-t["count"], len(t["text"])))
    return themes[:TOP_N]


async def for_rows(rows: list[dict]) -> dict:
    """Themes for one variant's reaction rows: {"objections": [...], "likes": [...]}."""
    import asyncio

    objections, likes = await asyncio.gather(
        group([list(r.get("top_objections") or []) for r in rows]),
        group([list(r.get("top_likes") or []) for r in rows]),
    )
    return {"objections": objections, "likes": likes}


async def warm_up() -> None:
    """One tiny call so the first real test doesn't pay connection setup."""
    try:
        await _embed(["warm up", "ready"])
    except Exception:  # noqa: BLE001
        log.warning("Embedding warm-up failed", exc_info=True)
