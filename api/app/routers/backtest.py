from fastapi import APIRouter

from app.services import fixtures

router = APIRouter()


@router.get("/backtest")
async def backtest() -> dict:
    # Real results from scripts/run_backtest.py (bundled, no Gemini calls); the sample only if it hasn't run yet.
    try:
        return fixtures.load("backtest.json")
    except FileNotFoundError:
        return fixtures.load("backtest_sample.json")
