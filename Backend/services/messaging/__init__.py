"""
Messaging package - Handle all communication with leads

Modules:
- whatsapp_service: Send messages via Twilio WhatsApp API
"""

from services.messaging.whatsapp_service import WhatsAppService

__all__ = ["WhatsAppService"]