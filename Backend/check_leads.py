import asyncio
from services.database.supabase_client import get_db_client
from services.database.repository import Repository

async def check():
    db = await get_db_client()
    repo = Repository(db)
    leads, _ = await repo.list_all_leads(limit=5, offset=0)
    for lead in leads:
        print(f"Lead: {lead['name']} ({lead['phone']}) - Status: {lead['status']}")

asyncio.run(check())
