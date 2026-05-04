from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_config
from services.telephony.twilio_client import TwilioClient


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["Calls"])


class OutboundCallRequest(BaseModel):
	phone_number: str = Field(..., description="Destination phone number in E.164 format")
	webhook_path: str = Field(default="/api/webhook/twilio/voice", description="Twilio webhook path to use for the call")


@router.post("/outbound")
async def initiate_call(payload: OutboundCallRequest):
	settings = get_config()
	if not settings.has_twilio:
		raise HTTPException(status_code=503, detail="Twilio is not configured in the backend env file.")

	client = TwilioClient()
	result = client.create_outbound_call(to_number=payload.phone_number, webhook_path=payload.webhook_path)
	return {
		"call_sid": result.sid,
		"status": result.status,
		"destination": payload.phone_number,
	}


@router.post("/whatsapp")
async def send_whatsapp_message(payload: OutboundCallRequest):
	settings = get_config()
	if not settings.twilio_whatsapp_from:
		raise HTTPException(status_code=503, detail="TWILIO_WHATSAPP_FROM is not configured in the backend env file.")

	client = TwilioClient()
	response = client.send_whatsapp_message(
		to_number=payload.phone_number,
		body="Hello from Sambhaash AI. Thanks for connecting with us.",
	)
	return {
		"sid": response.get("sid"),
		"status": response.get("status"),
		"to": payload.phone_number,
	}


@router.get("/status/{call_sid}")
async def get_call_status(call_sid: str):
	return {
		"call_sid": call_sid,
		"status": "tracked_by_twilio",
		"message": "Use Twilio Console or add a status callback webhook for live updates.",
	}
