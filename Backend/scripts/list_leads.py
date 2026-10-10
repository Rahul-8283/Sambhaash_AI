"""Print the five most recent leads (read-only)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.database.repository import Repository  # noqa: E402
from services.database.supabase_client import get_db_client  # noqa: E402


async def main() -> None:
    repo = Repository(await get_db_client())
    leads, _ = await repo.list_all_leads(limit=5, offset=0)
    for lead in leads:
        print(f"Lead: {lead['name']} ({lead['phone']}) - Status: {lead['status']}")


if __name__ == "__main__":
    asyncio.run(main())
