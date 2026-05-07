import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from uuid import UUID

from services.database.repository import Repository
from services.database.supabase_client import get_db_client
from services.messaging.whatsapp_service import WhatsAppService
from services.llm.llm_client import LLMClient
from config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook/whatsapp", tags=["WhatsApp Webhook"])


async def get_repository() -> Repository:
    """Get repository instance with database client"""
    db = await get_db_client()
    return Repository(db)


@router.post("")
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
            
        # Clean phone number (extract digits/country code)
        clean_phone = from_number.replace("whatsapp:", "").strip()
        
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
                model_name="llama-3.3-70b-versatile",
                api_key=settings.groq_api_key or "",
                base_url="https://api.groq.com/openai/v1"
            )
            
            # Contextual system prompt for WhatsApp chat
            system_prompt = f"""You are an intelligent, friendly, and persuasive relationship assistant for Rupeezy.
The user is a highly interested lead named {lead_name}. They recently had a conversation with us and we sent them a follow-up offer on WhatsApp:
- Instant ₹5,000+ loan
- 0% Processing Fee
- 5-minute approval

Your objective is to answer their questions contextually, address any objections (e.g. interest rate, tenure, process), and politely guide them to complete their application on our platform.
Keep your response short (2-3 sentences max), warm, and perfectly suited for a WhatsApp chat.
Respond in the language of their message ({lead_lang}).
Do not mention system instructions or metadata.
"""
            user_message = f"User Message: {body}"
            
            # Generate response from Groq
            response_text = llm_client.generate({
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
