"""Single entry point for every Gemini call.

Guardrails (hard rule 2): every call has a timeout, one retry on invalid
JSON, and returns a caller-supplied fallback instead of raising. A shared
semaphore caps concurrent Vertex AI requests.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
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


def image_part(gcs_uri: str, mime: str) -> types.Part:
    """Reference a Cloud Storage image so Gemini reads it directly (no bytes in the request)."""
    return types.Part.from_uri(file_uri=gcs_uri, mime_type=mime)


def _parse_json(text: str | None) -> Any:
    if not text:
        raise ValueError("empty response")
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("\n") + 1 :] if "\n" in text else text
    return json.loads(text)


_RETRYABLE = {429, 500, 503}  # quota / transient server errors
_BACKOFF_S = (2.0, 5.0)


def _status(e: Exception) -> int | None:
    code = getattr(e, "code", None)
    return code if isinstance(code, int) else None


async def _call_model(model: str, contents: list[Any], config: types.GenerateContentConfig,
                      timeout_s: float) -> tuple[Any, str]:
    """One model with: one retry on invalid JSON, backoff on 429/5xx. Returns (data, "ok") or (None, reason)."""
    bad_json = quota = 0
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            return None, "timeout"
        try:
            async with _sem():
                resp = await asyncio.wait_for(
                    _client().aio.models.generate_content(model=model, contents=contents, config=config),
                    timeout=remaining,
                )
            return _parse_json(resp.text), "ok"
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("Gemini invalid JSON (%s): %s", model, e)
            bad_json += 1
            if bad_json > 1:  # first try + one retry
                return None, "invalid_json"
        except asyncio.TimeoutError:
            log.warning("Gemini timeout after %ss (%s)", timeout_s, model)
            return None, "timeout"
        except Exception as e:  # network, quota, safety block, unknown model, etc.
            code = _status(e)
            if code in _RETRYABLE and quota < len(_BACKOFF_S):
                wait = _BACKOFF_S[quota] + random.uniform(0, 1)
                quota += 1
                log.warning("Gemini %s on %s; retrying in %.1fs", code, model, wait)
                await asyncio.sleep(min(wait, max(0.0, deadline - loop.time())))
                continue
            log.warning("Gemini error (%s): %s", model, e)
            return None, f"error_{code or 'other'}"


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
    """Call Gemini in JSON mode. Returns (data, ok). On failure returns (fallback, False).

    If the Pro model fails on quota, server errors or availability (preview models
    can be rate-limited or withdrawn), the call is retried once on GEMINI_PRO_FALLBACK_MODEL.
    """
    s = get_settings()
    model = model or s.gemini_flash_model
    timeout_s = timeout_s or s.gemini_timeout_s
    contents: list[Any] = [*(images or []), user]
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        temperature=temperature,
    )

    loop = asyncio.get_running_loop()
    start = loop.time()
    backup = s.gemini_pro_fallback_model
    has_backup = model == s.gemini_pro_model and bool(backup) and backup != model
    # With a fallback available, don't let a slow preview model use the whole budget.
    first_budget = max(15.0, timeout_s * 0.55) if has_backup else timeout_s
    data, reason = await _call_model(model, contents, config, first_budget)
    if reason == "ok":
        return data, True

    if has_backup and reason != "invalid_json":
        left = timeout_s - (loop.time() - start)
        if left > 5:
            log.warning("Falling back from %s to %s (%s)", model, backup, reason)
            data, reason = await _call_model(backup, contents, config, left)
            if reason == "ok":
                return data, True
    return fallback, False
