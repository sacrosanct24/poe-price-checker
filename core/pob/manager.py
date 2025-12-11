"""
Character profile manager - stores and manages PoB character profiles.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.pob.models import BuildCategory, CharacterProfile, PoBBuild, PoBItem
from core.pob.decoder import PoBDecoder

logger = logging.getLogger(__name__)


class CharacterManager:
    """
    Manages stored character profiles for upgrade comparisons.

    Stores profiles in a JSON file for persistence.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the character manager.

        Args:
            storage_path: Path to store character profiles
        """
        self.storage_path = storage_path or Path(__file__).parent.parent.parent / "data" / "characters.json"
        self._profiles: Dict[str, CharacterProfile] = {}
        self._active_profile_name: Optional[str] = None
        self._load_profiles()

    def _load_profiles(self) -> None:
        """Load profiles from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Handle both old format (flat dict) and new format (with _meta)
                if "_meta" in data:
                    self._active_profile_name = data["_meta"].get("active_profile")
                    profiles_data = data.get("profiles", {})
                else:
                    profiles_data = data
                for name, profile_data in profiles_data.items():
                    self._profiles[name] = self._deserialize_profile(profile_data)
                logger.info(f"Loaded {len(self._profiles)} character profiles")
            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")

    def _save_profiles(self) -> None:
        """Save profiles to storage file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "_meta": {
                    "active_profile": self._active_profile_name,
                },
                "profiles": {
                    name: self._serialize_profile(profile)
                    for name, profile in self._profiles.items()
                },
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    def _serialize_profile(self, profile: CharacterProfile) -> dict:
        """Serialize a profile to dict for JSON storage."""
        result = {
            "name": profile.name,
            "pob_code": profile.pob_code,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "notes": profile.notes,
            "categories": profile.categories,
            "is_upgrade_target": profile.is_upgrade_target,
            "build": {
                "class_name": profile.build.class_name,
                "ascendancy": profile.build.ascendancy,
                "level": profile.build.level,
                "main_skill": profile.build.main_skill,
                "stats": profile.build.stats,  # PoB calculated stats
                "items": {
                    slot: {
                        "slot": item.slot,
                        "rarity": item.rarity,
                        "name": item.name,
                        "base_type": item.base_type,
                        "item_level": item.item_level,
                        "quality": item.quality,
                        "sockets": item.sockets,
                        "implicit_mods": item.implicit_mods,
                        "explicit_mods": item.explicit_mods,
                    }
                    for slot, item in profile.build.items.items()
                },
            },
        }
        # Add priorities if they exist
        if profile.priorities is not None:
            result["priorities"] = profile.priorities.to_dict()
        # Add cached archetype if computed
        if profile._archetype is not None:
            result["archetype"] = profile._archetype.to_dict()
        # Add build library fields
        result["tags"] = profile.tags
        result["guide_url"] = profile.guide_url
        result["ssf_friendly"] = profile.ssf_friendly
        result["favorite"] = profile.favorite
        return result

    def _deserialize_profile(self, data: dict) -> CharacterProfile:
        """Deserialize a profile from dict."""
        build_data = data.get("build", {})
        build = PoBBuild(
            class_name=build_data.get("class_name", ""),
            ascendancy=build_data.get("ascendancy", ""),
            level=build_data.get("level", 1),
            main_skill=build_data.get("main_skill", ""),
            stats=build_data.get("stats", {}),  # PoB calculated stats
        )

        for slot, item_data in build_data.get("items", {}).items():
            build.items[slot] = PoBItem(
                slot=item_data.get("slot", ""),
                rarity=item_data.get("rarity", "RARE"),
                name=item_data.get("name", ""),
                base_type=item_data.get("base_type", ""),
                item_level=item_data.get("item_level", 0),
                quality=item_data.get("quality", 0),
                sockets=item_data.get("sockets", ""),
                implicit_mods=item_data.get("implicit_mods", []),
                explicit_mods=item_data.get("explicit_mods", []),
            )

        # Load priorities if they exist
        priorities = None
        if "priorities" in data:
            try:
                from core.build_priorities import BuildPriorities
                priorities = BuildPriorities.from_dict(data["priorities"])
            except Exception as e:
                logger.warning(f"Failed to load priorities: {e}")

        # Load cached archetype if it exists
        archetype = None
        if "archetype" in data:
            try:
                from core.build_archetype import BuildArchetype
                archetype = BuildArchetype.from_dict(data["archetype"])
            except Exception as e:
                logger.warning(f"Failed to load archetype: {e}")

        return CharacterProfile(
            name=data.get("name", ""),
            build=build,
            pob_code=data.get("pob_code", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            notes=data.get("notes", ""),
            categories=data.get("categories", []),
            is_upgrade_target=data.get("is_upgrade_target", False),
            priorities=priorities,
            _archetype=archetype,
            tags=data.get("tags", []),
            guide_url=data.get("guide_url", ""),
            ssf_friendly=data.get("ssf_friendly", False),
            favorite=data.get("favorite", False),
        )

    def add_from_pob_code(self, name: str, pob_code: str, notes: str = "") -> CharacterProfile:
        """
        Add a character from a PoB code.

        Args:
            name: Character name
            pob_code: PoB share code or pastebin URL
            notes: Optional notes

        Returns:
            Created CharacterProfile
        """
        from datetime import datetime

        build = PoBDecoder.from_code(pob_code)
        now = datetime.now().isoformat()

        profile = CharacterProfile(
            name=name,
            build=build,
            pob_code=pob_code,
            created_at=now,
            updated_at=now,
            notes=notes,
        )

        self._profiles[name] = profile
        self._save_profiles()

        logger.info(f"Added character profile: {name}")
        return profile

    def get_profile(self, name: str) -> Optional[CharacterProfile]:
        """Get a character profile by name."""
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all profile names."""
        return list(self._profiles.keys())

    def delete_profile(self, name: str) -> bool:
        """Delete a character profile."""
        if name in self._profiles:
            del self._profiles[name]
            self._save_profiles()
            return True
        return False

    def get_active_profile(self) -> Optional[CharacterProfile]:
        """Get the active profile for upgrade checking."""
        if self._active_profile_name and self._active_profile_name in self._profiles:
            return self._profiles[self._active_profile_name]
        # Fallback to first profile if no active set
        if self._profiles:
            return next(iter(self._profiles.values()))
        return None

    def set_active_profile(self, name: str) -> bool:
        """
        Set the active profile for upgrade checking.

        Args:
            name: Name of the profile to set as active

        Returns:
            True if successful, False if profile not found
        """
        if name not in self._profiles:
            logger.warning(f"Cannot set active profile: '{name}' not found")
            return False

        self._active_profile_name = name
        self._save_profiles()
        logger.info(f"Set active profile: {name}")
        return True

    def set_build_categories(self, name: str, categories: List[str]) -> bool:
        """
        Set categories for a build profile.

        Args:
            name: Profile name
            categories: List of category values (from BuildCategory enum)

        Returns:
            True if successful, False if profile not found
        """
        if name not in self._profiles:
            return False

        # Validate categories
        valid_categories = [c.value for c in BuildCategory]
        profile = self._profiles[name]
        profile.categories = [c for c in categories if c in valid_categories]
        self._save_profiles()
        logger.info(f"Set categories for '{name}': {profile.categories}")
        return True

    def add_build_category(self, name: str, category: str) -> bool:
        """Add a single category to a build."""
        if name not in self._profiles:
            return False

        try:
            cat = BuildCategory(category)
            self._profiles[name].add_category(cat)
            self._save_profiles()
            return True
        except ValueError:
            logger.warning(f"Invalid category: {category}")
            return False

    def remove_build_category(self, name: str, category: str) -> bool:
        """Remove a single category from a build."""
        if name not in self._profiles:
            return False

        try:
            cat = BuildCategory(category)
            self._profiles[name].remove_category(cat)
            self._save_profiles()
            return True
        except ValueError:
            return False

    def set_upgrade_target(self, name: str, is_target: bool = True) -> bool:
        """
        Mark a build as the upgrade target (the build you're actively gearing).

        Args:
            name: Profile name
            is_target: Whether this build is the upgrade target

        Returns:
            True if successful
        """
        if name not in self._profiles:
            return False

        # Clear previous upgrade target if setting a new one
        if is_target:
            for profile in self._profiles.values():
                profile.is_upgrade_target = False

        self._profiles[name].is_upgrade_target = is_target
        self._save_profiles()
        logger.info(f"Set upgrade target: {name} = {is_target}")
        return True

    def get_upgrade_target(self) -> Optional[CharacterProfile]:
        """Get the build marked as upgrade target."""
        for profile in self._profiles.values():
            if profile.is_upgrade_target:
                return profile
        # Fall back to active profile
        return self.get_active_profile()

    def set_priorities(self, name: str, priorities: Any) -> bool:
        """
        Set build priorities for a profile.

        Args:
            name: Profile name
            priorities: BuildPriorities object

        Returns:
            True if successful
        """
        if name not in self._profiles:
            return False

        self._profiles[name].priorities = priorities
        self._save_profiles()
        logger.info(f"Updated priorities for: {name}")
        return True

    def get_priorities(self, name: str) -> Optional[Any]:
        """
        Get build priorities for a profile.

        Returns BuildPriorities or None if not set.
        """
        if name not in self._profiles:
            return None
        return self._profiles[name].priorities

    def get_builds_by_category(self, category: str) -> List[CharacterProfile]:
        """Get all builds with a specific category."""
        return [
            p for p in self._profiles.values()
            if category in p.categories
        ]

    def get_available_categories(self) -> List[dict]:
        """Get list of available categories with descriptions."""
        return [
            {"value": c.value, "name": c.name.replace("_", " ").title()}
            for c in BuildCategory
        ]

    def update_profile(self, name: str, **kwargs) -> bool:
        """
        Update profile fields.

        Args:
            name: Profile name
            **kwargs: Fields to update (notes, tags, guide_url, ssf_friendly, favorite)

        Returns:
            True if successful
        """
        if name not in self._profiles:
            return False

        from datetime import datetime
        profile = self._profiles[name]

        for key, value in kwargs.items():
            if hasattr(profile, key) and key not in ("name", "build", "pob_code"):
                setattr(profile, key, value)

        profile.updated_at = datetime.now().isoformat()
        self._save_profiles()
        logger.info(f"Updated profile '{name}': {list(kwargs.keys())}")
        return True

    def set_tags(self, name: str, tags: List[str]) -> bool:
        """Set tags for a build profile."""
        return self.update_profile(name, tags=tags)

    def add_tag(self, name: str, tag: str) -> bool:
        """Add a tag to a build profile."""
        if name not in self._profiles:
            return False
        profile = self._profiles[name]
        if tag not in profile.tags:
            profile.tags.append(tag)
            self._save_profiles()
        return True

    def remove_tag(self, name: str, tag: str) -> bool:
        """Remove a tag from a build profile."""
        if name not in self._profiles:
            return False
        profile = self._profiles[name]
        if tag in profile.tags:
            profile.tags.remove(tag)
            self._save_profiles()
        return True

    def set_guide_url(self, name: str, url: str) -> bool:
        """Set guide URL for a build profile."""
        return self.update_profile(name, guide_url=url)

    def set_ssf_friendly(self, name: str, ssf_friendly: bool) -> bool:
        """Set SSF-friendly status for a build profile."""
        return self.update_profile(name, ssf_friendly=ssf_friendly)

    def toggle_favorite(self, name: str) -> bool:
        """Toggle favorite status for a build profile."""
        if name not in self._profiles:
            return False
        profile = self._profiles[name]
        profile.favorite = not profile.favorite
        self._save_profiles()
        return True

    def get_favorite_builds(self) -> List[CharacterProfile]:
        """Get all favorite builds."""
        return [p for p in self._profiles.values() if p.favorite]

    def get_ssf_builds(self) -> List[CharacterProfile]:
        """Get all SSF-friendly builds."""
        return [p for p in self._profiles.values() if p.ssf_friendly]

    def get_builds_by_tag(self, tag: str) -> List[CharacterProfile]:
        """Get all builds with a specific tag."""
        return [p for p in self._profiles.values() if tag in p.tags]

    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all builds."""
        tags = set()
        for profile in self._profiles.values():
            tags.update(profile.tags)
        return sorted(tags)

    def search_builds(
        self,
        query: str = "",
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        ssf_only: bool = False,
        favorites_only: bool = False,
    ) -> List[CharacterProfile]:
        """
        Search builds with multiple filters.

        Args:
            query: Search string (matches name, notes, ascendancy)
            categories: Filter by categories (any match)
            tags: Filter by tags (any match)
            ssf_only: Only show SSF-friendly builds
            favorites_only: Only show favorites

        Returns:
            List of matching profiles
        """
        results = list(self._profiles.values())

        if query:
            query_lower = query.lower()
            results = [
                p for p in results
                if query_lower in p.name.lower()
                or query_lower in p.notes.lower()
                or query_lower in p.build.ascendancy.lower()
                or query_lower in p.build.main_skill.lower()
            ]

        if categories:
            results = [
                p for p in results
                if any(c in p.categories for c in categories)
            ]

        if tags:
            results = [
                p for p in results
                if any(t in p.tags for t in tags)
            ]

        if ssf_only:
            results = [p for p in results if p.ssf_friendly]

        if favorites_only:
            results = [p for p in results if p.favorite]

        return results

    def export_profile(self, name: str) -> Optional[dict]:
        """
        Export a profile as a JSON-serializable dict.

        Args:
            name: Profile name to export

        Returns:
            Dict with profile data or None if not found
        """
        if name not in self._profiles:
            return None
        return self._serialize_profile(self._profiles[name])

    def import_profile(self, data: dict, overwrite: bool = False) -> Optional[str]:
        """
        Import a profile from exported data.

        Args:
            data: Profile data dict
            overwrite: If True, overwrite existing profile with same name

        Returns:
            Profile name if successful, None if failed
        """
        try:
            name = data.get("name", "")
            if not name:
                logger.error("Import failed: no name in profile data")
                return None

            if name in self._profiles and not overwrite:
                # Generate unique name
                base_name = name
                counter = 1
                while name in self._profiles:
                    name = f"{base_name} ({counter})"
                    counter += 1
                data["name"] = name

            profile = self._deserialize_profile(data)
            self._profiles[profile.name] = profile
            self._save_profiles()
            logger.info(f"Imported profile: {profile.name}")
            return profile.name
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return None

    def get_all_profiles(self) -> List[CharacterProfile]:
        """Get all profiles as a list."""
        return list(self._profiles.values())
