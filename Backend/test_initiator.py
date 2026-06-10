import asyncio
import logging
import sys
from uuid import UUID

from services.database.supabase_client import get_db_client
from services.database.repository import Repository
from worker.call_initiator import CallInitiator

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def test_call():
    initiator = CallInitiator()
    await initiator.startup()
    
    # Get the NEW lead
    db = await get_db_client()
    repo = Repository(db)
    leads, _ = await repo.list_leads_by_status("NEW", limit=1, offset=0)
    
    if not leads:
        print("No NEW leads found.")
        return
        
    lead = leads[0]
    print(f"Testing call for lead: {lead['name']} ({lead['phone']})")
    
    # Try calling
    success = await initiator.initiate_call_for_lead(lead)
    print(f"Call initiation success: {success}")
    
    await initiator.shutdown()

asyncio.run(test_call())
