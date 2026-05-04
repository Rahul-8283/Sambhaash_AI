import asyncio
import logging
from typing import Optional
from datetime import datetime
from uuid import UUID

from config import get_config
from services.database.supabase_client import get_db_client, close_db_client
from services.database.repository import Repository
from services.telephony.twilio_client import TwilioClient
from services.database.models import LeadStatus

logger = logging.getLogger(__name__)

# Import call_sessions cache from webhook routes
# This allows us to register sessions before calls are made
from api.routes.webhook_routes import call_sessions


class CallInitiator:
    """
    Finds NEW leads and initiates automatic outbound calls.
    
    Runs as a periodic scheduler task.
    """
    
    def __init__(self):
        self.config = get_config()
        self.db_client: Optional[any] = None
        self.repository: Optional[Repository] = None
        self.twilio_client = TwilioClient()
        
    async def startup(self):
        """Initialize database connection."""
        try:
            self.db_client = await get_db_client()
            self.repository = Repository(self.db_client)
            logger.info("✅ Call Initiator startup complete")
        except Exception as e:
            logger.error(f"❌ Call Initiator startup failed: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup on shutdown."""
        try:
            if self.db_client:
                await close_db_client()
            logger.info("Call Initiator shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def start_scheduler(self, poll_interval: int = 30):
        """
        Start the scheduler loop to check for NEW leads.
        
        Args:
            poll_interval: Seconds between polls
        """
        logger.info(f"🚀 Call Initiator Scheduler started (poll_interval={poll_interval}s)")
        
        await self.startup()
        
        try:
            while True:
                try:
                    await self.find_and_call_new_leads()
                    await asyncio.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"Scheduler loop error: {e}")
                    await asyncio.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Call Initiator interrupted by user")
        finally:
            await self.shutdown()
    
    async def find_and_call_new_leads(self):
        """
        Find all NEW leads and initiate calls for each.
        
        This is the main scheduler task.
        """
        try:
            # Query for NEW leads
            leads, total = await self.repository.list_leads_by_status(
                status=LeadStatus.NEW.value,
                limit=50,
                offset=0
            )
            
            if not leads:
                logger.debug("No NEW leads to call")
                return
            
            logger.info(f"Found {len(leads)} NEW leads to call")
            
            # Process each lead
            for lead in leads:
                try:
                    await self.initiate_call_for_lead(lead)
                except Exception as e:
                    logger.error(f"Failed to call lead {lead['id']}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error finding NEW leads: {e}")
    
    async def initiate_call_for_lead(self, lead: dict) -> bool:
        """
        Initiate a Twilio call for a lead.
        
        Args:
            lead: Lead record from database
            
        Returns:
            True if call initiated successfully, False otherwise
        """
        lead_id = lead.get("id")
        phone = lead.get("phone")
        name = lead.get("name", "Customer")
        
        if not phone:
            logger.warning(f"Lead {lead_id} has no phone number")
            return False
        
        try:
            # Check if Twilio is configured
            if not self.twilio_client.configured:
                logger.warning("Twilio is not configured - skipping call")
                return False
            
            # Create call session in database BEFORE calling
            call_session = await self.repository.create_call_session(
                lead_id=UUID(lead_id),
                language_detected=lead.get("language", "en")
            )
            
            logger.info(f"Created call session: {call_session['id']}")
            
            # Pre-register session in webhook cache
            # This way when Twilio calls back, the session info is ready
            # We'll update it with actual call_sid once we get it back
            pending_session_key = f"pending_{lead_id}"
            call_sessions[pending_session_key] = {
                "lead_id": lead_id,
                "session_id": str(call_session['id']),
                "turn_count": 0,
                "phone": phone,
                "pending": True
            }
            logger.debug(f"Pre-registered session in cache: {pending_session_key}")
            
            # Initiate Twilio call
            result = self.twilio_client.create_outbound_call(
                to_number=phone,
                webhook_path="/api/webhook/twilio/voice"
            )
            
            if result.sid:
                call_sid = result.sid
                logger.info(f"✅ Call initiated for {name} ({phone})")
                logger.info(f"   Call SID: {call_sid}")
                logger.info(f"   Session ID: {call_session['id']}")
                
                # Move from pending to actual call_sid
                if pending_session_key in call_sessions:
                    call_sessions[call_sid] = call_sessions.pop(pending_session_key)
                    call_sessions[call_sid]["pending"] = False
                    logger.debug(f"Moved session from {pending_session_key} to {call_sid}")
                
                # Update lead status to CONTACTED
                await self.repository.update_lead(
                    lead_id=UUID(lead_id),
                    status=LeadStatus.CONTACTED.value
                )
                
                return True
            else:
                logger.error(f"Failed to initiate call: {result.status}")
                # Cleanup pending session
                if pending_session_key in call_sessions:
                    del call_sessions[pending_session_key]
                return False
        
        except Exception as e:
            logger.error(f"Exception initiating call for lead {lead_id}: {e}")
            # Cleanup pending session
            pending_session_key = f"pending_{lead_id}"
            if pending_session_key in call_sessions:
                del call_sessions[pending_session_key]
            return False
