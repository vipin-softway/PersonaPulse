import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import backtest, demo, health

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("personapulse")

settings = get_settings()

app = FastAPI(
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
