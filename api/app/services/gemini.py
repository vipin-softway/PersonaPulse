"""Single entry point for every Gemini call.

Guardrails (hard rule 2): every call has a timeout, one retry on invalid
JSON, and returns a caller-supplied fallback instead of raising. A shared
semaphore caps concurrent Vertex AI requests.
"""

from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings

log = logging.getLogger("personapulse.gemini")

_semaphore: asyncio.Semaphore | None = None


@lru_cache
def _client() -> genai.Client:
    s = get_settings()
    # vertexai=True + no api_key => Application Default Credentials.
    return genai.Client(vertexai=True, project=s.gcp_project, location=s.gcp_location)


def _sem() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(get_settings().gemini_concurrency)
    return _semaphore


def _parse_json(text: str | None) -> Any:
    if not text:
        raise ValueError("empty response")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("\n") + 1 :] if "\n" in text else text
    return json.loads(text)


async def generate_json(
    *,
    system: str,
    user: str,
    fallback: Any,
    model: str | None = None,
    temperature: float = 0.7,
    images: list[types.Part] | None = None,
    timeout_s: int | None = None,
) -> tuple[Any, bool]:
    """Call Gemini in JSON mode. Returns (data, ok). On failure returns (fallback, False)."""
    s = get_settings()
    model = model or s.gemini_flash_model
    timeout_s = timeout_s or s.gemini_timeout_s
    contents: list[Any] = [*(images or []), user]
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        temperature=temperature,
    )

    for attempt in (1, 2):  # first try + one retry
        try:
            async with _sem():
                resp = await asyncio.wait_for(
                    _client().aio.models.generate_content(
                        model=model, contents=contents, config=config
                    ),
                    timeout=timeout_s,
                )
            return _parse_json(resp.text), True
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("Gemini invalid JSON (attempt %d, %s): %s", attempt, model, e)
            continue  # retry once on bad JSON
        except asyncio.TimeoutError:
            log.warning("Gemini timeout after %ss (%s)", timeout_s, model)
            break
        except Exception as e:  # network, quota, safety block, etc.
            log.warning("Gemini error (%s): %s", model, e)
            break
    return fallback, False
