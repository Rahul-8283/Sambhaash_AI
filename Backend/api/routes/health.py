from __future__ import annotations

from fastapi import APIRouter

from Backend.config import get_settings


router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
	settings = get_settings()
	return {
		"status": "ok",
		"mode": settings.MODE,
		"twilio_configured": settings.has_twilio,
		"openai_configured": settings.has_openai,
	}


@router.get("/ready")
async def ready_check():
	settings = get_settings()
	return {
		"ready": True,
		"services": {
			"twilio": settings.has_twilio,
			"openai": settings.has_openai,
			"supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
		},
	}
