from fastapi import APIRouter

from app.services import fixtures

router = APIRouter()


@router.get("/backtest")
async def backtest() -> dict:
    # Phase 5: read backtest_results from BigQuery first, falling back to this bundle.
    return fixtures.load("backtest_sample.json")
