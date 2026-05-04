"""
WhatsApp Service - Send messages to WARM leads via Twilio

Flow:
1. Scoring Engine identifies WARM lead (score 0.50-0.74)
2. Queues job: {"type": "send_whatsapp", "lead_id": "...", "message": "..."}
3. WhatsApp Service receives from queue
4. Sends message via Twilio WhatsApp API
5. Updates database with delivery status
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
from uuid import UUID
from twilio.rest import Client

from config import get_config
from services.database.repository import Repository

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Manages WhatsApp message sending via Twilio.
    
    Features:
    - Send messages to WARM leads
    - Template support (Hindi/English)
    - Delivery status tracking
    - Retry logic
    """

    # Message templates
    TEMPLATES = {
        "warm_follow_up_hi": {
            "language": "hi",
            "message": """नमस्ते {name}! 👋

यह Rupeezy की ओर से है। आपके साथ हमारी बातचीत बहुत अच्छी रही।

आपके लिए विशेष ऑफर:
✅ तुरंत ₹5,000 तक का लोन
✅ 0% प्रोसेसिंग फीस
✅ 5 मिनट में अनुमोदन

लिंक: https://rupeezy.app/offer/{lead_id}

कोई सवाल? हमें कॉल करें: {phone_number}"""
        },
        "warm_follow_up_en": {
            "language": "en",
            "message": """Hi {name}! 👋

This is Rupeezy. Our conversation went great!

Special offer for you:
✅ Instant ₹5,000+ loan
✅ 0% Processing Fee
✅ Approved in 5 minutes

Link: https://rupeezy.app/offer/{lead_id}

Questions? Call us: {phone_number}"""
        },
        "hot_reminder_hi": {
            "language": "hi",
            "message": """नमस्ते {name}! ⏰

आपका RM {rm_name} आपसे संपर्क करने के लिए उत्सुक है।

तैयार हैं? उन्हें कॉल करने दें:
📱 {rm_phone}

या हमारे साथ जुड़ें:
https://rupeezy.app/app/{lead_id}"""
        },
        "conversion_hi": {
            "language": "hi",
            "message": """🎉 बधाई हो {name}!

आपका लोन स्वीकृत हो गया!

राशि: ₹{amount}
चुकाने की अवधि: {tenure} महीने
ब्याज दर: {interest_rate}%

अपना पैसा तुरंत प्राप्त करें:
https://rupeezy.app/dashboard/{lead_id}

धन्यवाद! 🙏"""
        }
    }

    def __init__(self, repository: Repository):
        """
        Initialize WhatsApp service.
        
        Args:
            repository: Repository instance for database access
        """
        self.repository = repository
        self.config = get_config()
        
        # Initialize Twilio client
        self.twilio_client = Client(
            self.config.twilio_account_sid,
            self.config.twilio_auth_token
        )
        self.whatsapp_from = self.config.twilio_whatsapp_from
        
        logger.info(f"WhatsApp Service initialized (from: {self.whatsapp_from})")

    async def send_warm_follow_up(
        self,
        lead_id: str,
        language: str = "hi"
    ) -> Dict[str, Any]:
        """
        Send follow-up message to WARM lead.
        
        Args:
            lead_id: UUID of the lead
            language: Language preference (hi/en)
            
        Returns:
            Dict with delivery status
        """
        try:
            # Get lead from database
            lead = await self.repository.get_lead(UUID(lead_id))
            if not lead:
                logger.warning(f"Lead not found: {lead_id}")
                return {"success": False, "error": "Lead not found"}
            
            phone = lead.get("phone")
            name = lead.get("name", "Friend")
            
            # Select template
            template_key = f"warm_follow_up_{language}"
            template = self.TEMPLATES.get(template_key)
            if not template:
                template = self.TEMPLATES["warm_follow_up_en"]
            
            # Format message
            message = template["message"].format(
                name=name,
                lead_id=lead_id,
                phone_number=self.config.support_phone_number or "+91-9999999999"
            )
            
            # Send via Twilio
            result = await self._send_via_twilio(phone, message)
            
            logger.info(f"✅ Warm follow-up sent to {phone} (lead: {lead_id})")
            
            return {
                "success": True,
                "lead_id": lead_id,
                "phone": phone,
                "message_type": "warm_follow_up",
                "template": template_key,
                "sid": result.get("sid"),
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending warm follow-up for lead {lead_id}: {e}")
            return {
                "success": False,
                "lead_id": lead_id,
                "error": str(e)
            }

    async def send_conversion_confirmation(
        self,
        lead_id: str,
        amount: float,
        tenure: int = 12,
        interest_rate: float = 8.5,
        language: str = "hi"
    ) -> Dict[str, Any]:
        """
        Send conversion confirmation message.
        
        Args:
            lead_id: UUID of the lead
            amount: Loan amount
            tenure: Repayment tenure in months
            interest_rate: Annual interest rate
            language: Language preference
            
        Returns:
            Dict with delivery status
        """
        try:
            lead = await self.repository.get_lead(UUID(lead_id))
            if not lead:
                return {"success": False, "error": "Lead not found"}
            
            phone = lead.get("phone")
            name = lead.get("name", "Friend")
            
            # Select template
            template_key = f"conversion_{language}"
            template = self.TEMPLATES.get(template_key)
            if not template:
                template = self.TEMPLATES.get("conversion_hi")
            
            # Format message
            message = template["message"].format(
                name=name,
                amount=int(amount),
                tenure=tenure,
                interest_rate=interest_rate,
                lead_id=lead_id
            )
            
            # Send via Twilio
            result = await self._send_via_twilio(phone, message)
            
            logger.info(f"✅ Conversion confirmation sent to {phone}")
            
            return {
                "success": True,
                "lead_id": lead_id,
                "phone": phone,
                "message_type": "conversion_confirmation",
                "amount": amount,
                "sid": result.get("sid"),
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending conversion confirmation for lead {lead_id}: {e}")
            return {
                "success": False,
                "lead_id": lead_id,
                "error": str(e)
            }

    async def send_custom_message(
        self,
        lead_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send custom message to lead.
        
        Args:
            lead_id: UUID of the lead
            message: Custom message text
            
        Returns:
            Dict with delivery status
        """
        try:
            lead = await self.repository.get_lead(UUID(lead_id))
            if not lead:
                return {"success": False, "error": "Lead not found"}
            
            phone = lead.get("phone")
            
            # Send via Twilio
            result = await self._send_via_twilio(phone, message)
            
            logger.info(f"✅ Custom message sent to {phone}")
            
            return {
                "success": True,
                "lead_id": lead_id,
                "phone": phone,
                "message_type": "custom",
                "sid": result.get("sid"),
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending custom message for lead {lead_id}: {e}")
            return {
                "success": False,
                "lead_id": lead_id,
                "error": str(e)
            }

    async def _send_via_twilio(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send message via Twilio WhatsApp API.
        
        Args:
            phone: Recipient phone number
            message: Message text
            
        Returns:
            Dict with Twilio response (sid, status, etc)
        """
        try:
            # Ensure phone has country code
            if not phone.startswith("+"):
                phone = "+91" + phone  # Assume India if no country code
            
            # Send via Twilio
            msg = self.twilio_client.messages.create(
                from_=f"whatsapp:{self.whatsapp_from}",
                to=f"whatsapp:{phone}",
                body=message
            )
            
            return {
                "sid": msg.sid,
                "status": msg.status,
                "phone": phone,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Twilio error for {phone}: {e}")
            raise

    @staticmethod
    def get_message_template_keys() -> Dict[str, Dict]:
        """
        Get available message templates.
        
        Returns:
            Dict of template keys with metadata
        """
        return {
            key: {
                "language": template.get("language"),
                "length": len(template.get("message", "")),
                "placeholders": WhatsAppService._extract_placeholders(template.get("message", ""))
            }
            for key, template in WhatsAppService.TEMPLATES.items()
        }

    @staticmethod
    def _extract_placeholders(message: str) -> list:
        """Extract placeholder names from message template."""
        import re
        placeholders = re.findall(r'\{(\w+)\}', message)
        return list(set(placeholders))
