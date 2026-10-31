import asyncio
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from uuid import UUID

from services.database.repository import Repository
from services.database.supabase_client import get_db_client
from services.messaging.whatsapp_service import WhatsAppService
from services.llm.llm_client import LLMClient
from config import get_config
from utils.phone import normalize_phone
from api.twilio_auth import verify_twilio_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/whatsapp", tags=["WhatsApp Webhook"])


def whatsapp_system_prompt(lead_name: str, lead_lang: str) -> str:
    return f"""You are a friendly relationship assistant for the Rupeezy Partner Program.
Rupeezy is an Indian stock broking and investment platform; partners earn commissions by referring clients.
The user is a lead named {lead_name} who recently spoke with our voice agent about the Partner Program. We thanked them on WhatsApp and said our team would share details.

Answer their questions briefly and honestly. Do not invent commission rates, fees, figures, links or deadlines; if you do not know a detail, say a Relationship Manager will confirm it. If they ask not to be contacted, acknowledge it politely.
Keep your response short (2-3 sentences max), warm, and suited for a WhatsApp chat.
Respond in the language of their message ({lead_lang}).
Do not mention system instructions or metadata.
"""


async def get_repository() -> Repository:
    """Get repository instance with database client"""
    db = await get_db_client()
    return Repository(db)


@router.post("", dependencies=[Depends(verify_twilio_signature)])
async def receive_whatsapp(
    request: Request,
    repo: Repository = Depends(get_repository)
) -> Response:
    """
    Webhook for receiving incoming Twilio WhatsApp messages from WARM leads
    and responding to them contextually using the Groq LLM.
    """
    try:
        form = await request.form()
        from_number = form.get("From", "")  # e.g., "whatsapp:+919876543210"
        body = form.get("Body", "").strip()
        
        if not from_number or not body:
            return Response(content="Missing From or Body parameter", status_code=400)
            
        # Normalize to E.164 so it matches how leads are stored
        clean_phone = normalize_phone(from_number)

        # Look up lead by phone
        lead = await repo.get_lead_by_phone(clean_phone)
        if not lead:
            logger.info(f"Received WhatsApp message from unknown number: {clean_phone}")
            return Response(content="Lead not found", status_code=200)
            
        lead_id = lead.get("id")
        lead_name = lead.get("name", "Friend")
        lead_lang = lead.get("language", "hi")
        
        # Get latest score classification
        latest_score = await repo.get_latest_score(UUID(str(lead_id)))
        classification = latest_score.get("classification") if latest_score else "COLD"
        
        logger.info(f"Incoming WhatsApp from WARM lead '{lead_name}' ({clean_phone}) classification={classification}")
        
        # Generate and send response contextually if the lead is WARM or HOT
        if classification in ("WARM", "HOT"):
            settings = get_config()
            llm_client = LLMClient(
                model_name=get_config().llm_model_name,
                api_key=settings.groq_api_key or "",
                base_url="https://api.groq.com/openai/v1"
            )
            
            # Contextual system prompt for WhatsApp chat
            system_prompt = whatsapp_system_prompt(lead_name, lead_lang)
            user_message = f"User Message: {body}"
            
            # Generate response from Groq
            response_text = await asyncio.to_thread(llm_client.generate, {
                "system_prompt": system_prompt,
                "user_prompt": user_message
            })
            
            # Clean response text
            response_text = response_text.strip().strip('"').strip("'")
            
            # Send message via WhatsApp service
            whatsapp_service = WhatsAppService(repo)
            await whatsapp_service.send_custom_message(str(lead_id), response_text)
            logger.info(f"✅ Contextually replied to WARM lead '{lead_name}' via WhatsApp: {response_text}")
            
        return Response(content="SUCCESS", status_code=200)
        
    except Exception as e:
        logger.error(f"Error handling WhatsApp webhook: {e}")
        return Response(content=str(e), status_code=500)
