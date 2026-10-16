"""Live tests: POST /tests runs Prompt 4 on the panel's live personas; GET /tests/{id} shows results."""

from __future__ import annotations

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
    await tests_store.save_variant(test_id=test_id, variant="original", panel=body.panel, product=product,
                                   rows=rows, run=run, image_uri=image_uri, ip_hash=_ip_hash(request), themes=themes)
    variant = aggregate_variant("original", product, tests_store.with_display(rows, personas), segments, themes)
    result = build_test_result(test_id, [variant], created_at=run["run_at"], panel=body.panel, run=run)
    tests_store.remember(result)
    marks["saved"] = time.monotonic() - t0
    log.info("Test %s timings: %s", test_id, {k: round(v, 1) for k, v in marks.items()})
    return result


@router.get("/tests/{test_id}")
async def get_test(test_id: str) -> dict:
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


@router.get("/tests/{test_id}/image")
async def get_image(test_id: str, variant: str = "original") -> Response:
    _check_id(test_id)
    from google.cloud import bigquery

    from app.services import bq

    rows = await bq.query(
        f"SELECT image_uri FROM {bq.table('tests')} WHERE test_id = @id AND variant = @v AND image_uri IS NOT NULL LIMIT 1",
        [bigquery.ScalarQueryParameter("id", "STRING", test_id), bigquery.ScalarQueryParameter("v", "STRING", variant)])
    if not rows:
        raise HTTPException(status_code=404, detail="No image for this test.")
    data, mime = await storage.load_image(rows[0]["image_uri"])
    return Response(content=data, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})
