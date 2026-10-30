import asyncio

import services.rm_allocator as alloc
from services.rm_allocator import RM, least_loaded, parse_roster


def test_parse_roster_with_and_without_phones():
    assert parse_roster("Asha:+919800000001, Ravi ,,") == [RM("Asha", "+919800000001"), RM("Ravi", None)]
    assert parse_roster("") == []


def test_least_loaded_wins_and_order_breaks_ties():
    roster = [RM("A", None), RM("B", None), RM("C", None)]
    assert least_loaded(roster, {"A": 3, "B": 1, "C": 1}).name == "B"
    assert least_loaded(roster, {}).name == "A"


class _Repo:
    async def get_rm_open_counts(self, names):
        return {"Asha": 2, "Ravi": 0}


def _with_roster(monkeypatch, raw, default="Auto"):
    class Cfg:
        rm_roster = raw
        default_rm_name = default
    monkeypatch.setattr(alloc, "get_config", lambda: Cfg)


def test_choose_rm_uses_roster_load(monkeypatch):
    _with_roster(monkeypatch, "Asha:+911,Ravi:+912")
    assert asyncio.run(alloc.choose_rm(_Repo())) == RM("Ravi", "+912")


def test_choose_rm_falls_back_to_default(monkeypatch):
    _with_roster(monkeypatch, "", default="Team")
    assert asyncio.run(alloc.choose_rm(_Repo())) == RM("Team", None)
