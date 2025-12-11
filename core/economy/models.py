"""
League Economy Data Models.

Enums and dataclasses for economic snapshots and history.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class LeagueMilestone(Enum):
    """League timeline milestones for economic snapshots."""

    LEAGUE_START = "league_start"  # Day 1-3
    WEEK_1_END = "week_1_end"  # Day 7
    MONTH_1_END = "month_1_end"  # Day 30
    LEAGUE_END = "league_end"  # Final snapshot


@dataclass
class CurrencySnapshot:
    """Currency exchange rate snapshot at a point in time."""

    league: str
    date: datetime
    divine_to_chaos: float
    exalt_to_chaos: Optional[float] = None
    mirror_to_chaos: Optional[float] = None
    annul_to_chaos: Optional[float] = None


@dataclass
class UniqueSnapshot:
    """Top unique item prices at a point in time."""

    league: str
    date: datetime
    item_name: str
    base_type: str
    chaos_value: float
    divine_value: Optional[float] = None
    rank: int = 0  # Rank by value (1 = most expensive)


@dataclass
class LeagueEconomySnapshot:
    """Complete economic snapshot for a league milestone."""

    league: str
    milestone: LeagueMilestone
    snapshot_date: datetime
    divine_to_chaos: float
    exalt_to_chaos: Optional[float] = None
    top_uniques: List[UniqueSnapshot] = field(default_factory=list)

    @property
    def display_milestone(self) -> str:
        """Human-readable milestone name."""
        names = {
            LeagueMilestone.LEAGUE_START: "League Start",
            LeagueMilestone.WEEK_1_END: "Week 1",
            LeagueMilestone.MONTH_1_END: "Month 1",
            LeagueMilestone.LEAGUE_END: "End of League",
        }
        return names.get(self.milestone, self.milestone.value)
