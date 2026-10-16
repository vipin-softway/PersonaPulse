"""Live tests: POST /tests runs Prompt 4 on the panel's live personas; GET /tests/{id} shows results."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from google.genai import types
from pydantic import BaseModel, Field, field_validator

from app.panels import PANELS
from app.ratelimit import _client_ip, rate_limit
from app.services import personas as persona_store
from app.config import get_settings
from app.services import insights as insight_service
from app.services import storage, tests_store, themes as theme_service
from app.services.aggregate import aggregate_variant, build_test_result
from app.services.gemini import image_part
from app.services.simulate import run_reactions

log = logging.getLogger("personapulse.tests")
router = APIRouter()

_TEST_ID = re.compile(r"^[a-f0-9]{8,32}$")
BUSY = "Our AI customers are busy right now. Please try again in a minute, or view the demo test."


class NewTest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=600)
    price_inr: float = Field(gt=0, le=1_000_000)
    pack_size: str = Field(min_length=1, max_length=60)
    channel: str = Field(min_length=2, max_length=60)
    panel: str = "accessories"
    competitors: str | None = Field(default=None, max_length=200)
    image_base64: str | None = None
    image_mime: str | None = None  # ignored: the type is read from the file itself

    @field_validator("panel")
    @classmethod
    def known_panel(cls, v: str) -> str:
        if v not in PANELS:
            raise ValueError("unknown panel")
        return v

    @field_validator("name", "description", "pack_size", "channel", "competitors")
    @classmethod
    def strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


def _ip_hash(request: Request) -> str:
    return hashlib.sha256(f"personapulse:{_client_ip(request)}".encode()).hexdigest()[:16]


def _check_id(test_id: str) -> None:
    if not _TEST_ID.match(test_id):
        raise HTTPException(status_code=404, detail="Test not found.")


@router.post("/tests", dependencies=[Depends(rate_limit)])
async def create_test(body: NewTest, request: Request) -> dict:
    test_id = uuid.uuid4().hex[:16]
    t0 = time.monotonic()
    marks: dict[str, float] = {}

    image, image_uri = None, None
    if body.image_base64:
        try:
            data, mime = storage.decode_image(body.image_base64)
        except storage.ImageError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        image_uri = await storage.save_image(test_id, "original", data, mime)
        # Gemini reads the stored copy by URI; without a bucket, send the bytes inline.
        image = image_part(image_uri, mime) if image_uri else types.Part.from_bytes(data=data, mime_type=mime)

    try:
        personas, segments = await persona_store.load_panel(body.panel)
    except Exception:  # noqa: BLE001
        log.exception("Loading personas for %s failed", body.panel)
        raise HTTPException(status_code=503, detail=BUSY) from None
    if not personas:
        raise HTTPException(status_code=503, detail=BUSY)
    marks["personas"] = time.monotonic() - t0

    product = {"name": body.name, "description": body.description, "price_inr": body.price_inr,
               "pack_size": body.pack_size, "channel": body.channel, "competitors": body.competitors,
               "has_image": image is not None}
    rows, run = await run_reactions(personas, product, image)
    marks["reactions"] = time.monotonic() - t0
    run["run_at"] = tests_store.now_iso()
    log.info("Test %s [%s]: %d/%d personas answered in %.1fs", test_id, body.panel, len(rows), len(personas),
             run["duration_s"])
    if len(rows) < max(5, len(personas) // 2):
        raise HTTPException(status_code=503, detail=BUSY)

    themes = await theme_service.for_rows(rows)
    marks["themes"] = time.monotonic() - t0
    display = tests_store.with_display(rows, personas)
    variant = aggregate_variant("original", product, display, segments, themes)
    await tests_store.save_variant(test_id=test_id, variant="original", panel=body.panel, product=product,
                                   rows=rows, run=run, image_uri=image_uri, ip_hash=_ip_hash(request), themes=themes)
    result = build_test_result(test_id, [variant], created_at=run["run_at"], panel=body.panel, run=run)
    _summarize_later(test_id, product, variant, display)
    tests_store.remember(result)
    marks["saved"] = time.monotonic() - t0
    log.info("Test %s timings: %s", test_id, {k: round(v, 1) for k, v in marks.items()})
    return result


_background: set[asyncio.Task] = set()  # keep references so tasks aren't garbage-collected


def _summarize_later(test_id: str, product: dict, variant: dict, display: list[dict]) -> None:
    """Prompt 6 takes ~20 s on Pro, so results are returned first and the summary is filled in after.

    The variant dict is shared with the cached result, so GET /tests/{id} sees the summary once it lands.
    """
    variant["insights"] = None
    variant["insights_pending"] = True

    async def run() -> None:
        try:
            summary = await insight_service.summarize(product, variant, display)
            variant["insights"] = summary
            if summary:
                await tests_store.save_insight(test_id, variant["variant"], "summary", summary,
                                               get_settings().gemini_pro_model)
        except Exception:  # noqa: BLE001
            log.exception("Insights for %s/%s failed", test_id, variant["variant"])
        finally:
            variant["insights_pending"] = False

    task = asyncio.create_task(run())
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _load(test_id: str) -> dict:
    _check_id(test_id)
    cached = tests_store.recent(test_id)
    if cached:
        return cached
    try:
        result = await tests_store.load_test(test_id)
    except Exception:  # noqa: BLE001
        log.exception("Loading test %s failed", test_id)
        raise HTTPException(status_code=503, detail="Results are temporarily unavailable. Please try again.") from None
    if result is None:
        raise HTTPException(status_code=404, detail="Test not found.")
    tests_store.remember(result)
    return result


@router.get("/tests/{test_id}")
async def get_test(test_id: str) -> dict:
    return await _load(test_id)


class Improve(BaseModel):
    variant_id: str | None = Field(default=None, max_length=8)
    constraints: str | None = Field(default=None, max_length=300)


_busy: set[tuple[str, str]] = set()  # (test_id, variant) retests in flight


@router.post("/tests/{test_id}/improve", dependencies=[Depends(rate_limit)])
async def improve(test_id: str, body: Improve) -> dict:
    """No variant_id: Prompt 7 suggests variants. With variant_id: retest it on the same AI customers."""
    result = await _load(test_id)
    if result.get("is_demo"):
        raise HTTPException(status_code=400, detail="The demo can't be changed. Run your own test to try this.")
    original = result["variants"][0]

    if not body.variant_id:
        if result.get("suggestions") and not body.constraints:
            return result
        for _ in range(40):  # Prompt 7 builds on Prompt 6: wait for a summary still being written
            if not original.get("insights_pending"):
                break
            await asyncio.sleep(1)
        suggestions = await insight_service.suggest(original["product"], original.get("insights"), body.constraints)
        if not suggestions:
            raise HTTPException(status_code=503, detail="We couldn't come up with improvements right now. Please try again.")
        await tests_store.save_insight(test_id, None, "suggestions", suggestions, get_settings().gemini_pro_model)
        result = {**result, "suggestions": suggestions}
        tests_store.remember(result)
        return result

    vid = body.variant_id
    if any(v["variant"] == vid for v in result["variants"]):
        return result
    suggestion = next((x for x in result.get("suggestions") or [] if x["variant_id"] == vid), None)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="That suggestion wasn't found. Please refresh the page.")
    if (test_id, vid) in _busy:
        raise HTTPException(status_code=409, detail="This variant is already being retested. Please wait a moment.")
    _busy.add((test_id, vid))
    try:
        return await _retest(result, suggestion)
    finally:
        _busy.discard((test_id, vid))


async def _retest(result: dict, suggestion: dict) -> dict:
    test_id, panel, vid = result["test_id"], result.get("panel") or "accessories", suggestion["variant_id"]
    original = result["variants"][0]["product"]
    up = suggestion["updated_product"]
    # Reuse the original image only when the variant doesn't change the packaging.
    reuse_image = bool(original.get("has_image")) and not suggestion.get("imagen_prompt")
    image, uri = None, None
    if reuse_image:
        uri = await tests_store.image_uri(test_id, "original")
        if uri:
            data, mime = await storage.load_image(uri)
            image = image_part(uri, mime)
    product = {"name": up["product_name"], "description": up["product_description"], "price_inr": up["price_inr"],
               "pack_size": up["pack_size"], "channel": up["channel"], "competitors": original.get("competitors"),
               "has_image": image is not None}
    try:
        personas, segments = await persona_store.load_panel(panel)
    except Exception:  # noqa: BLE001
        log.exception("Loading personas for %s failed", panel)
        raise HTTPException(status_code=503, detail=BUSY) from None
    rows, run = await run_reactions(personas, product, image)
    run["run_at"] = tests_store.now_iso()
    if len(rows) < max(5, len(personas) // 2):
        raise HTTPException(status_code=503, detail=BUSY)
    themes = await theme_service.for_rows(rows)
    display = tests_store.with_display(rows, personas)
    variant = aggregate_variant(vid, product, display, segments, themes)
    await tests_store.save_variant(test_id=test_id, variant=vid, panel=panel, product=product, rows=rows, run=run,
                                   image_uri=uri if image else None, ip_hash=None, themes=themes,
                                   parent_variant="original")
    _summarize_later(test_id, product, variant, display)
    log.info("Retest %s/%s: %d personas in %.1fs", test_id, vid, len(rows), run["duration_s"])
    updated = {**result, "variants": [*result["variants"], variant]}
    tests_store.remember(updated)
    return updated


@router.get("/tests/{test_id}/image")
async def get_image(test_id: str, variant: str = "original") -> Response:
    _check_id(test_id)
    uri = await tests_store.image_uri(test_id, variant[:8])
    if not uri:
        raise HTTPException(status_code=404, detail="No image for this test.")
    data, mime = await storage.load_image(uri)
    return Response(content=data, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})
