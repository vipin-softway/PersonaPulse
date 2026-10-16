import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import backtest, demo, health, tests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("personapulse")
# google-genai logs every request at INFO; keep our logs readable.
for noisy in ("google_genai", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm caches in the background so the first live test after a cold start is fast.
    async def warm() -> None:
        from app.panels import PANELS
        from app.services import personas, themes

        for panel in PANELS:
            try:
                await personas.load_panel(panel)
            except Exception:  # noqa: BLE001
                log.warning("Warm-up: loading %s personas failed", panel, exc_info=True)
        await themes.warm_up()

    task = asyncio.create_task(warm()) if settings.gcp_project else None
    yield
    if task:
        task.cancel()


app = FastAPI(
    lifespan=lifespan,
    title="PersonaPulse API",
    description="Self-serve AI focus groups. All results are AI-simulated customers.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    # Never leak a stack trace to judges; log it for us instead.
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong on our side. Please try again in a moment."},
    )


app.include_router(health.router)
app.include_router(demo.router)
app.include_router(backtest.router)
app.include_router(tests.router)
