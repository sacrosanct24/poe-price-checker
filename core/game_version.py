"""
Game version enumeration for Path of Exile 1 and Path of Exile 2.
Used throughout the application to determine which game's data to use.
"""

from enum import Enum
from typing import Optional


class GameVersion(Enum):
    """
    Enum for Path of Exile game versions.

    POE1 and POE2 are separate games with different:
    - Economies (separate leagues)
    - Trade APIs
    - Item systems
    - Pricing sources
    """
    POE1 = "poe1"
    POE2 = "poe2"

    def __str__(self) -> str:
        """String representation"""
        return self.value

    def display_name(self) -> str:
        """Human-readable name"""
        return {
            GameVersion.POE1: "Path of Exile 1",
            GameVersion.POE2: "Path of Exile 2"
        }[self]

    @classmethod
    def from_string(cls, value: str) -> Optional['GameVersion']:
        """
        Create GameVersion from string.

        Args:
            value: "poe1", "poe2", "PoE1", "PoE2", etc.

        Returns:
            GameVersion enum or None if invalid
        """
        value_lower = value.lower().strip()

        for version in cls:
            if version.value == value_lower:
                return version

        return None

    @classmethod
    def get_default(cls) -> 'GameVersion':
        """Get default game version (PoE1)"""
        return cls.POE1


class GameConfig:
    """
    Configuration for a specific game version.
    Stores league, currency rates, etc.

    PoE1 uses Chaos as base currency, Divine as high-value.
    PoE2 uses Exalted as base currency, Divine as high-value.
    """

    def __init__(
            self,
            game_version: GameVersion,
            league: str = "Standard",
            divine_chaos_rate: float = 1.0,
            # PoE2-specific: Exalted is the base currency
            divine_exalted_rate: float = 80.0,
            chaos_exalted_rate: float = 7.0,
    ):
        """
        Args:
            game_version: Which game (POE1 or POE2)
            league: Current league name
            divine_chaos_rate: PoE1: Divine orb to chaos conversion rate
            divine_exalted_rate: PoE2: Divine orb to exalted conversion rate
            chaos_exalted_rate: PoE2: Chaos orb to exalted conversion rate
        """
        self.game_version = game_version
        self.league = league
        # PoE1 currency rates
        self.divine_chaos_rate = divine_chaos_rate
        # PoE2 currency rates
        self.divine_exalted_rate = divine_exalted_rate
        self.chaos_exalted_rate = chaos_exalted_rate

    def __repr__(self) -> str:
        if self.is_poe2():
            return f"GameConfig(game={self.game_version}, league={self.league}, divine_exalt_rate={self.divine_exalted_rate:.1f})"
        return f"GameConfig(game={self.game_version}, league={self.league}, divine_chaos_rate={self.divine_chaos_rate:.1f})"

    def get_api_league_name(self) -> str:
        """
        Get the league name formatted for API calls.
        Some APIs are case-sensitive.
        """
        return self.league

    def is_poe1(self) -> bool:
        """Check if this is PoE1"""
        return self.game_version == GameVersion.POE1

    def is_poe2(self) -> bool:
        """Check if this is PoE2"""
        return self.game_version == GameVersion.POE2

    def get_base_currency_name(self) -> str:
        """
        Get the name of the base currency for this game.

        PoE1: Chaos Orb
        PoE2: Exalted Orb
        """
        return "exalted" if self.is_poe2() else "chaos"

    def get_divine_rate(self) -> float:
        """
        Get divine orb conversion rate to base currency.

        PoE1: Divine per Chaos
        PoE2: Divine per Exalted
        """
        if self.is_poe2():
            return self.divine_exalted_rate
        return self.divine_chaos_rate


# Testing
if __name__ == "__main__":
    # Test game version enum
    print("=== Game Version Enum Test ===")

    poe1 = GameVersion.POE1
    poe2 = GameVersion.POE2

    print(f"PoE1: {poe1} - {poe1.display_name()}")
    print(f"PoE2: {poe2} - {poe2.display_name()}")

    # Test from_string
    from_str = GameVersion.from_string("poe2")
    print(f"From string 'poe2': {from_str}")

    from_str_caps = GameVersion.from_string("POE1")
    print(f"From string 'POE1': {from_str_caps}")

    # Test default
    default = GameVersion.get_default()
    print(f"Default: {default}")

    # Test game config
    print("\n=== Game Config Test ===")

    config_poe1 = GameConfig(GameVersion.POE1, league="Keepers of the Flame", divine_chaos_rate=317.2)
    print(config_poe1)
    print(f"Is PoE1? {config_poe1.is_poe1()}")
    print(f"Is PoE2? {config_poe1.is_poe2()}")

    config_poe2 = GameConfig(GameVersion.POE2, league="Standard Settlers", divine_chaos_rate=150.0)
    print(config_poe2)
    print(f"Is PoE1? {config_poe2.is_poe1()}")
    print(f"Is PoE2? {config_poe2.is_poe2()}")
