from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_config
from services.telephony.twilio_client import TwilioClient


logger = logging.getLogger(__name__)

from fastapi import Depends
from api.auth import get_current_user

router = APIRouter(prefix="/api/calls", tags=["Calls"], dependencies=[Depends(get_current_user)])
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
	client = TwilioClient()
	try:
		call = client.get_call(call_sid)
	except requests.exceptions.HTTPError as e:
		if e.response is not None and e.response.status_code == 404:
			raise HTTPException(status_code=404, detail="Call not found")
		logger.error(f"Twilio call status lookup failed for {call_sid}: {e}")
		raise HTTPException(status_code=502, detail="Could not fetch call status from Twilio")
	except Exception as e:
		logger.error(f"Twilio call status lookup failed for {call_sid}: {e}")
		raise HTTPException(status_code=502, detail="Could not fetch call status from Twilio")

	return {
		"call_sid": call_sid,
		"status": call.get("status"),
		"duration": call.get("duration"),
		"to": call.get("to"),
		"from": call.get("from"),
		"start_time": call.get("start_time"),
		"end_time": call.get("end_time"),
	}
