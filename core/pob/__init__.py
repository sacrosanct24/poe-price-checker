"""
Path of Building (PoB) Integration Package.

Provides functionality to:
1. Decode PoB pastebin/share codes into build data
2. Extract character equipment for upgrade comparison
3. Compare items against character's current gear
4. Store multiple character profiles

For new code, import directly from this package:
    from core.pob import PoBDecoder, CharacterManager, UpgradeChecker
"""

from core.pob.checker import UpgradeChecker
from core.pob.decoder import (  # URL helper functions (for internal use, but exported for compatibility)
    PoBDecoder,
    _is_pastebin_url,
    _is_pobbin_url,
    _url_host_matches,
)
from core.pob.manager import CharacterManager

# Re-export all public classes for backward compatibility
from core.pob.models import BuildCategory, CharacterProfile, PoBBuild, PoBItem

__all__ = [
    # Models
    "BuildCategory",
    "PoBItem",
    "PoBBuild",
    "CharacterProfile",
    # Decoder
    "PoBDecoder",
    "_is_pastebin_url",
    "_is_pobbin_url",
    "_url_host_matches",
    # Manager
    "CharacterManager",
    # Checker
    "UpgradeChecker",
]
