from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import call_routes, health, webhook_routes
from config import get_settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


settings = get_settings()

app = FastAPI(title="Sambhaash AI Backend", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(webhook_routes.router)
app.include_router(call_routes.router)


@app.get("/")
async def root():
	return {
		"service": "Sambhaash AI",
		"layer": "Person 1 - Input (Telephony + STT)",
		"status": "running",
	}


@app.on_event("startup")
async def startup_event() -> None:
	logger.info("Sambhaash AI backend starting in %s mode", settings.MODE)
	logger.info("Twilio configured: %s", settings.has_twilio)
	logger.info("OpenAI configured: %s", settings.has_openai)


if __name__ == "__main__":
	import uvicorn

	uvicorn.run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
