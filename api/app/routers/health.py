from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "service": "personapulse-api",
        "version": "0.1.0",
        "project_configured": bool(s.gcp_project),
        "location": s.gcp_location,
        "max_live_personas": s.max_live_personas,
        "label": "AI-simulated customers",
    }
