"""execute_update must cope with command tags that carry no row count (DDL)."""

import pytest

from services.database.supabase_client import SupabaseClient


class _Conn:
    def __init__(self, tag):
        self.tag = tag

    async def execute(self, query, *params):
        return self.tag


class _Acquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


class _Pool:
    def __init__(self, tag):
        self.conn = _Conn(tag)

    def acquire(self):
        return _Acquire(self.conn)


def _client(tag):
    client = SupabaseClient.__new__(SupabaseClient)
    client.pool = _Pool(tag)
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("tag,expected", [
    ("UPDATE 3", 3),
    ("INSERT 0 1", 1),
    ("DELETE 0", 0),
    ("ALTER TABLE", 0),
    ("CREATE INDEX", 0),
    ("", 0),
])
async def test_execute_update_row_counts(tag, expected):
    assert await _client(tag).execute_update("sql", ()) == expected
