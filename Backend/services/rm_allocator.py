"""Pick the relationship manager for a HOT lead from the configured roster."""

from typing import Dict, List, NamedTuple, Optional

from config import get_config


class RM(NamedTuple):
    name: str
    phone: Optional[str]


def parse_roster(raw: str) -> List[RM]:
    """'Asha:+919800000001, Ravi' -> [RM('Asha', '+919800000001'), RM('Ravi', None)]"""
    roster: List[RM] = []
    for entry in (raw or "").split(","):
        name, _, phone = entry.strip().partition(":")
        name, phone = name.strip(), phone.strip()
        if name:
            roster.append(RM(name, phone or None))
    return roster


def least_loaded(roster: List[RM], open_counts: Dict[str, int]) -> RM:
    """Fewest open (unconverted) assignments wins; roster order breaks ties."""
    return min(roster, key=lambda rm: open_counts.get(rm.name, 0))


async def choose_rm(repository) -> RM:
    config = get_config()
    roster = parse_roster(config.rm_roster)
    if not roster:
        return RM(config.default_rm_name or "Auto", None)
    counts = await repository.get_rm_open_counts([rm.name for rm in roster])
    return least_loaded(roster, counts)
