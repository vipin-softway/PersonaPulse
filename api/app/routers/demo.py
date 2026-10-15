from fastapi import APIRouter

from app.services import fixtures

router = APIRouter()


@router.get("/demo")
async def demo() -> dict:
    # Phase 4: read the saved demo test from BigQuery first, falling back to this bundle.
    return fixtures.load("demo.json")
