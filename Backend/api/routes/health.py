from __future__ import annotations

from fastapi import APIRouter

from config import get_config


router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
	settings = get_config()
	return {
		"status": "ok",
		"mode": settings.mode,
		"twilio_configured": settings.has_twilio,
		"openai_configured": settings.has_openai,
	}


@router.get("/ready")
async def ready_check():
	settings = get_config()
	return {
		"ready": True,
		"services": {
			"twilio": settings.has_twilio,
			"openai": settings.has_openai,
			"supabase": bool(settings.supabase_url and settings.supabase_service_role_key),
		},
	}
