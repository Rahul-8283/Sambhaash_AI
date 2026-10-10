"""
Place ONE real outbound call to the first NEW lead, to exercise the dialer.

This dials a real phone through Twilio and writes to whatever database
DATABASE_URL points at. Use a verified number and a development database.

    python scripts/place_test_call.py --yes
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.database.models import LeadStatus  # noqa: E402
from services.database.repository import Repository  # noqa: E402
from services.database.supabase_client import get_db_client  # noqa: E402
from worker.call_initiator import CallInitiator  # noqa: E402

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def place_call() -> None:
    initiator = CallInitiator()
    await initiator.startup()

    repo = Repository(await get_db_client())
    leads, _ = await repo.list_leads_by_status(LeadStatus.NEW.value, limit=1, offset=0)
    if not leads:
        print("No NEW leads found.")
        return

    lead = leads[0]
    print(f"Calling lead: {lead['name']} ({lead['phone']})")
    success = await initiator.initiate_call_for_lead(lead)
    print(f"Call initiation success: {success}")

    await initiator.shutdown()


if __name__ == "__main__":
    if "--yes" not in sys.argv:
        sys.exit("This places a real call. Re-run with --yes to confirm.")
    asyncio.run(place_call())
