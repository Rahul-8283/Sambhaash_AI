"""
Apply the SQL files in scripts/migrations/ in name order.

Every migration is written to be idempotent (IF NOT EXISTS), so re-running is
safe. This touches whatever database DATABASE_URL points at: do not run it
against the shared production Supabase without reviewing the files first.

    python scripts/migrate.py            # list what would run
    python scripts/migrate.py --apply    # run them
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.database.supabase_client import get_db_client  # noqa: E402

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


async def main(apply: bool) -> None:
    files = sorted(MIGRATIONS.glob("*.sql"))
    for path in files:
        print(("APPLY " if apply else "WOULD RUN ") + path.name)
    if not apply:
        print("\nRe-run with --apply to execute.")
        return

    db = await get_db_client()
    for path in files:
        await db.execute_update(path.read_text(), ())
        print(f"done  {path.name}")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
