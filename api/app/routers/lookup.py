from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.ratelimit import rate_limit
from app.services.lookup import lookup

router = APIRouter()


class Lookup(BaseModel):
    query: str = Field(min_length=2, max_length=120)


@router.post("/lookup", dependencies=[Depends(rate_limit)])
async def product_lookup(body: Lookup) -> dict:
    """Prompt 9: fill the test form from the web (Gemini + Google Search)."""
    result = await lookup(body.query.strip())
    if result is None:
        raise HTTPException(status_code=503, detail="We couldn't search the web right now. Please fill in the details yourself.")
    return result
