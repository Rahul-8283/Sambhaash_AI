"""
WhatsApp Service - Send messages to WARM leads via Twilio

Flow:
1. Scoring Engine identifies WARM lead (score 0.50-0.74)
2. Queues job: {"type": "send_whatsapp", "lead_id": "...", "message": "..."}
3. WhatsApp Service receives from queue
4. Sends message via Twilio WhatsApp API
5. Updates database with delivery status
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from uuid import UUID
from twilio.rest import Client

from config import get_config
from services.database.repository import Repository
from utils.language import to_language_code
from utils.phone import normalize_phone

logger = logging.getLogger(__name__)


# Warm follow-up copy per language: (greeting, thanks, next step, question label).
# The message thanks the caller for talking about the Rupeezy Partner Program and
# says the team will share details. It makes no offer, price or link claims.
# en/hi follow the original wording; the other languages are machine translations
# and need review by a native speaker before going to real leads.
_WARM_FOLLOW_UP_COPY = {
    "en": ("Hi {name}! 👋", "This is Rupeezy. Thank you for speaking with us about the Rupeezy Partner Program.",
           "Our team will share the details with you shortly.", "Questions? Call us"),
    "hi": ("नमस्ते {name}! 👋", "यह Rupeezy की ओर से है। Rupeezy पार्टनर प्रोग्राम के बारे में हमसे बात करने के लिए धन्यवाद।",
           "हमारी टीम जल्द ही आपको पूरी जानकारी भेजेगी।", "कोई सवाल? हमें कॉल करें"),
    "mr": ("नमस्कार {name}! 👋", "हे Rupeezy कडून आहे. Rupeezy पार्टनर प्रोग्रामबद्दल आमच्याशी बोलल्याबद्दल धन्यवाद.",
           "आमची टीम लवकरच तुम्हाला सविस्तर माहिती पाठवेल.", "काही प्रश्न? आम्हाला कॉल करा"),
    "bn": ("নমস্কার {name}! 👋", "এটি Rupeezy থেকে। Rupeezy পার্টনার প্রোগ্রাম সম্পর্কে আমাদের সঙ্গে কথা বলার জন্য ধন্যবাদ।",
           "আমাদের টিম শীঘ্রই আপনাকে বিস্তারিত তথ্য পাঠাবে।", "কোনো প্রশ্ন? আমাদের কল করুন"),
    "gu": ("નમસ્તે {name}! 👋", "આ Rupeezy તરફથી છે. Rupeezy પાર્ટનર પ્રોગ્રામ વિશે અમારી સાથે વાત કરવા બદલ આભાર.",
           "અમારી ટીમ ટૂંક સમયમાં તમને વિગતો મોકલશે.", "કોઈ પ્રશ્ન? અમને કૉલ કરો"),
    "pa": ("ਸਤ ਸ੍ਰੀ ਅਕਾਲ {name}! 👋", "ਇਹ Rupeezy ਵੱਲੋਂ ਹੈ। Rupeezy ਪਾਰਟਨਰ ਪ੍ਰੋਗਰਾਮ ਬਾਰੇ ਸਾਡੇ ਨਾਲ ਗੱਲ ਕਰਨ ਲਈ ਧੰਨਵਾਦ।",
           "ਸਾਡੀ ਟੀਮ ਜਲਦੀ ਹੀ ਤੁਹਾਨੂੰ ਪੂਰੀ ਜਾਣਕਾਰੀ ਭੇਜੇਗੀ।", "ਕੋਈ ਸਵਾਲ? ਸਾਨੂੰ ਕਾਲ ਕਰੋ"),
    "or": ("ନମସ୍କାର {name}! 👋", "ଏହା Rupeezy ପକ୍ଷରୁ। Rupeezy ପାର୍ଟନର ପ୍ରୋଗ୍ରାମ ବିଷୟରେ ଆମ ସହ କଥା ହେବା ପାଇଁ ଧନ୍ୟବାଦ।",
           "ଆମ ଟିମ୍ ଶୀଘ୍ର ଆପଣଙ୍କୁ ବିବରଣୀ ପଠାଇବ।", "କୌଣସି ପ୍ରଶ୍ନ? ଆମକୁ କଲ୍ କରନ୍ତୁ"),
    "ta": ("வணக்கம் {name}! 👋", "இது Rupeezy சார்பில். Rupeezy பார்ட்னர் திட்டம் குறித்து எங்களுடன் பேசியதற்கு நன்றி.",
           "எங்கள் குழு விரைவில் உங்களுக்கு விவரங்களை அனுப்பும்.", "கேள்விகள் உள்ளதா? எங்களை அழையுங்கள்"),
    "te": ("నమస్తే {name}! 👋", "ఇది Rupeezy నుండి. Rupeezy పార్టనర్ ప్రోగ్రామ్ గురించి మాతో మాట్లాడినందుకు ధన్యవాదాలు.",
           "మా బృందం త్వరలో మీకు వివరాలు పంపుతుంది.", "ఏవైనా ప్రశ్నలు? మాకు కాల్ చేయండి"),
    "kn": ("ನಮಸ್ಕಾರ {name}! 👋", "ಇದು Rupeezy ಕಡೆಯಿಂದ. Rupeezy ಪಾರ್ಟ್ನರ್ ಪ್ರೋಗ್ರಾಂ ಬಗ್ಗೆ ನಮ್ಮೊಂದಿಗೆ ಮಾತನಾಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು.",
           "ನಮ್ಮ ತಂಡ ಶೀಘ್ರದಲ್ಲೇ ನಿಮಗೆ ವಿವರಗಳನ್ನು ಕಳುಹಿಸುತ್ತದೆ.", "ಪ್ರಶ್ನೆಗಳಿವೆಯೇ? ನಮಗೆ ಕರೆ ಮಾಡಿ"),
    "ml": ("നമസ്കാരം {name}! 👋", "ഇത് Rupeezy യിൽ നിന്നാണ്. Rupeezy പാർട്ണർ പ്രോഗ്രാമിനെക്കുറിച്ച് ഞങ്ങളോട് സംസാരിച്ചതിന് നന്ദി.",
           "ഞങ്ങളുടെ ടീം ഉടൻ തന്നെ വിശദാംശങ്ങൾ അയയ്ക്കും.", "സംശയങ്ങളുണ്ടോ? ഞങ്ങളെ വിളിക്കുക"),
}


def _warm_follow_up_message(copy) -> str:
    greeting, thanks, next_step, question = copy
    return f"{greeting}\n\n{thanks}\n\n{next_step}\n\n{question}: {{phone_number}}"


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
        "hot_reminder_hi": {
            "language": "hi",
            "message": """नमस्ते {name}! ⏰

आपका RM {rm_name} आपसे संपर्क करने के लिए उत्सुक है।

तैयार हैं? उन्हें कॉल करने दें:
📱 {rm_phone}

या हमारे साथ जुड़ें:
https://rupeezy.app/app/{lead_id}"""
        },
        "conversion_en": {
            "language": "en",
            "message": """🎉 Welcome aboard, {name}!

You are now a Rupeezy partner. Your relationship manager will be in touch to help you get started.

Thank you! 🙏"""
        },
        "conversion_hi": {
            "language": "hi",
            "message": """🎉 स्वागत है, {name}!

अब आप Rupeezy के पार्टनर हैं। शुरुआत में मदद के लिए आपके रिलेशनशिप मैनेजर आपसे संपर्क करेंगे।

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
            template_key = f"warm_follow_up_{to_language_code(language)}"
            template = self.TEMPLATES.get(template_key)
            if not template:
                template = self.TEMPLATES["warm_follow_up_en"]
            
            # Format message
            message = template["message"].format(
                name=name,
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
        language: str = "hi"
    ) -> Dict[str, Any]:
        """
        Send conversion confirmation message.
        
        Args:
            lead_id: UUID of the lead
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
            template_key = f"conversion_{to_language_code(language)}"
            template = self.TEMPLATES.get(template_key)
            if not template:
                template = self.TEMPLATES.get("conversion_en")
            
            # Format message
            message = template["message"].format(name=name)
            
            # Send via Twilio
            result = await self._send_via_twilio(phone, message)
            
            logger.info(f"✅ Conversion confirmation sent to {phone}")
            
            return {
                "success": True,
                "lead_id": lead_id,
                "phone": phone,
                "message_type": "conversion_confirmation",
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

    async def send_to_number(self, phone: str, message: str) -> Dict[str, Any]:
        """Send a message to a phone number that is not a lead (e.g. an RM)."""
        try:
            result = await self._send_via_twilio(phone, message)
            return {"success": True, "phone": phone, "sid": result.get("sid")}
        except Exception as e:
            logger.error(f"Error sending message to {phone}: {e}")
            return {"success": False, "error": str(e)}

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
            phone = normalize_phone(phone)
            
            # Clean from_ number to ensure we don't duplicate 'whatsapp:' prefix
            from_number = self.whatsapp_from.replace('whatsapp:', '')
            
            # Send via Twilio
            # The Twilio SDK call is blocking; run it off the event loop
            msg = await asyncio.to_thread(
                self.twilio_client.messages.create,
                from_=f"whatsapp:{from_number}",
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


for _code, _copy in _WARM_FOLLOW_UP_COPY.items():
    WhatsAppService.TEMPLATES[f"warm_follow_up_{_code}"] = {
        "language": _code,
        "message": _warm_follow_up_message(_copy),
    }
