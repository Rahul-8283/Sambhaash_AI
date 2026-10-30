import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID

from config import get_config
from services.database.supabase_client import get_db_client, close_db_client
from services.database.repository import Repository
from services.telephony.twilio_client import TwilioClient
from services.database.models import LeadStatus
from services.ngrok_setup import load_ngrok_url
from utils.phone import normalize_phone
import requests

logger = logging.getLogger(__name__)



class CallInitiator:
    """
    Finds NEW leads and initiates automatic outbound calls.
    
    Runs as a periodic scheduler task.
    """
    
    def __init__(self):
        self.config = get_config()
        self.db_client: Optional[any] = None
        self.repository: Optional[Repository] = None
        
        # Load ngrok URL from file if in development mode (written by backend)
        ngrok_url = None
        if self.config.mode.lower() == "development":
            ngrok_url = load_ngrok_url()
            if ngrok_url:
                logger.info(f"[CALL_INIT] Using ngrok URL: {ngrok_url}")
                # Update config so TwilioClient uses it
                self.config.twilio_webhook_base_url = ngrok_url
        
        self.twilio_client = TwilioClient()
        
    async def startup(self):
        """Initialize database connection."""
        try:
            self.db_client = await get_db_client()
            self.repository = Repository(self.db_client)
            logger.info("[CALL_INIT] Startup complete")
        except Exception as e:
            logger.error(f"[CALL_INIT] Startup failed: {e}", exc_info=True)
            raise
    
    async def shutdown(self):
        """Cleanup on shutdown."""
        try:
            if self.db_client:
                await close_db_client()
            logger.info("[CALL_INIT] Shutdown complete")
        except Exception as e:
            logger.error(f"[CALL_INIT] Shutdown error: {e}")
    
    async def start_scheduler(self, poll_interval: int = 30):
        """
        Start the scheduler loop to check for NEW leads.
        
        Args:
            poll_interval: Seconds between polls
        """
        logger.info(f"[CALL_INIT] Scheduler started (poll_interval={poll_interval}s)")
        
        # Safe serial connection retry loop on boot to avoid parallel race conditions
        while not self.repository:
            try:
                await self.startup()
            except Exception as e:
                logger.warning(f"[CALL_INIT] Database connection failed ({e}). Retrying in 3 seconds...")
                await asyncio.sleep(3)
        
        try:
            while True:
                try:
                    await self.find_and_call_new_leads()
                    await self.find_and_call_nurture_leads()
                    await asyncio.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"[CALL_INIT] Scheduler loop error: {e}", exc_info=False)
                    await asyncio.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("[CALL_INIT] Interrupted by user")
        finally:
            await self.shutdown()
    
    async def find_and_call_new_leads(self):
        """
        Find all NEW leads and initiate calls for each.
        
        This is the main scheduler task.
        """
        if not self.repository:
            try:
                self.db_client = await get_db_client()
                self.repository = Repository(self.db_client)
            except Exception as e:
                logger.warning(f"[CALL_INIT] Connection retry failed: {e}. Waiting for network...")
                return
        try:
            # Query for NEW leads
            leads, total = await self.repository.list_leads_by_status(
                status=LeadStatus.NEW.value,
                limit=50,
                offset=0
            )
            
            if not leads:
                logger.debug("[CALL_INIT] No NEW leads to call")
                return
            
            logger.info(f"[CALL_INIT] Found {len(leads)} NEW leads to call")
            
            # Process each lead
            for lead in leads:
                try:
                    await self.initiate_call_for_lead(lead)
                except Exception as e:
                    logger.error(f"[CALL_INIT] Failed processing lead: {e}", exc_info=False)
                    continue
        
        except Exception as e:
            logger.error(f"[CALL_INIT] Error finding NEW leads: {e}", exc_info=False)
    
    def _within_call_window(self, now: Optional[datetime] = None) -> bool:
        """True during the allowed calling hours, in India Standard Time."""
        ist = timezone(timedelta(hours=5, minutes=30))
        hour = (now or datetime.now(ist)).astimezone(ist).hour
        return self.config.call_window_start_hour <= hour < self.config.call_window_end_hour

    async def find_and_call_nurture_leads(self):
        """Retry FOLLOW_UP leads that never answered, inside calling hours (opt-in)."""
        if not self.config.nurture_enabled or not self.repository:
            return
        if not self._within_call_window():
            return
        try:
            leads = await self.repository.list_nurture_candidates(
                cooldown_hours=self.config.nurture_cooldown_hours,
                max_attempts=self.config.nurture_max_attempts,
                limit=10,
            )
            if leads:
                logger.info(f"[CALL_INIT] Nurture: {len(leads)} FOLLOW_UP leads due another attempt")
            for lead in leads:
                try:
                    await self.initiate_call_for_lead(lead)
                except Exception as e:
                    logger.error(f"[CALL_INIT] Nurture call failed: {e}", exc_info=False)
        except Exception as e:
            logger.error(f"[CALL_INIT] Error finding nurture leads: {e}", exc_info=False)

    @staticmethod
    def _is_permanent_failure(error: Exception) -> bool:
        """
        True when retrying the same lead cannot succeed: an invalid phone number,
        or Twilio rejecting the request with a 4xx (bad number, unverified trial
        number, etc). Network errors and Twilio 5xx responses are transient.
        """
        if isinstance(error, ValueError):
            return True
        if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
            return 400 <= error.response.status_code < 500
        return False

    async def initiate_call_for_lead(self, lead: dict) -> bool:
        """
        Initiate a Twilio call for a lead.
        
        Args:
            lead: Lead record from database
            
        Returns:
            True if call initiated successfully, False otherwise
        """
        # Resolved before the try so the exception handler can always use them
        lead_id = None
        phone = lead.get("phone")

        try:
            # Handle UUID conversion - lead['id'] may already be UUID from asyncpg
            lead_id_raw = lead.get("id")
            if isinstance(lead_id_raw, UUID):
                lead_id = lead_id_raw
            else:
                lead_id = UUID(str(lead_id_raw))
            
            phone = lead.get("phone")
            name = lead.get("name", "Customer")
            
            if not phone:
                logger.warning(f"Lead {lead_id} has no phone number")
                return False

            # Dial E.164 numbers only; raises ValueError for unusable numbers
            phone = normalize_phone(phone)
            
            # Check if Twilio is configured
            if not self.twilio_client.configured:
                logger.warning("Twilio is not configured - skipping call")
                return False
            
            # Create call session in database BEFORE calling
            call_session = await self.repository.create_call_session(
                lead_id=lead_id,
                language_detected=lead.get("language", "en")
            )
            
            logger.info(f"Created call session: {call_session['id']}")
            
            
            # Initiate Twilio call
            result = self.twilio_client.create_outbound_call(
                to_number=phone,
                webhook_path=f"/api/webhook/twilio/voice?session_id={call_session['id']}&lead_id={lead_id}",
                status_callback_path=f"/api/webhook/twilio/status?session_id={call_session['id']}&lead_id={lead_id}"
            )
            
            if result.sid:
                call_sid = result.sid
                logger.info(f"[CALL] Initiated for {name} ({phone})")
                logger.info(f"[CALL] Call SID: {call_sid}")
                logger.info(f"[CALL] Session ID: {call_session['id']}")
                
                # Update lead status to CONTACTED
                await self.repository.update_lead(
                    lead_id=lead_id,
                    status=LeadStatus.CONTACTED.value
                )
                
                return True
            else:
                logger.error(f"Failed to initiate call: {result.status}")
                # Mark as REJECTED so it doesn't infinitely loop
                await self.repository.update_lead(
                    lead_id=lead_id,
                    status=LeadStatus.REJECTED.value
                )
                return False
        
        except Exception as e:
            logger.error(f"[CALL_INIT] Exception initiating call for {phone}: {e}", exc_info=False)
            
            if lead_id is None:
                return False

            # Only mark REJECTED for permanent failures. Transient errors leave the
            # lead NEW so the next poll retries it.
            if not self._is_permanent_failure(e):
                logger.warning(f"[CALL_INIT] Transient failure for lead {lead_id}; will retry on next poll")
                return False

            try:
                await self.repository.update_lead(
                    lead_id=lead_id,
                    status=LeadStatus.REJECTED.value
                )
            except Exception as update_err:
                logger.error(f"[CALL_INIT] Failed to mark lead as REJECTED: {update_err}")
                
            return False
