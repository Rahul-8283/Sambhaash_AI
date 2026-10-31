import asyncio
import uuid

from fastapi.testclient import TestClient

import main
from api.auth import get_current_user
from api.routes import rm_routes
from services.database.repository import Repository


class _DB:
    def __init__(self, fail_notes=False):
        self.fail_notes = fail_notes
        self.sql = []

    async def execute_update(self, query, params):
        self.sql.append((query, params))
        if "conversion_notes" in query and self.fail_notes:
            raise RuntimeError('column "conversion_notes" does not exist')
        return 1


def _repo(db):
    repo = Repository(db)

    async def noop_update_lead(*a, **kw):
        return None

    repo.update_lead = noop_update_lead
    return repo


def test_conversion_notes_are_saved():
    db = _DB()
    assert asyncio.run(_repo(db).mark_as_converted(uuid.uuid4(), "  paid the fee  "))
    assert any("conversion_notes" in q and p[1] == "paid the fee" for q, p in db.sql)


def test_no_notes_means_no_notes_write():
    db = _DB()
    asyncio.run(_repo(db).mark_as_converted(uuid.uuid4(), "   "))
    assert not any("conversion_notes" in q for q, _ in db.sql)


def test_conversion_still_succeeds_when_migration_001_is_missing():
    db = _DB(fail_notes=True)
    assert asyncio.run(_repo(db).mark_as_converted(uuid.uuid4(), "note")) is True


def test_unknown_lead_is_a_404_not_a_500():
    class Repo:
        async def get_lead(self, lead_id):
            return None

    main.app.dependency_overrides[get_current_user] = lambda: {"id": "u"}
    main.app.dependency_overrides[rm_routes.get_repository] = lambda: Repo()
    try:
        client = TestClient(main.app, base_url="http://localhost")
        response = client.post(f"/api/rm/Asha/{uuid.uuid4()}/complete", json={"notes": "x"})
        assert response.status_code == 404
    finally:
        main.app.dependency_overrides.clear()
