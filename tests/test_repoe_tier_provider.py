"""
Tests for RePoE Tier Provider Module.

Tests the RePoE tier data extraction functionality including:
- RePoETier dataclass
- RePoETierProvider tier extraction methods
- BaseItemRecommendation and BaseItemRecommender
- Singleton getter functions
"""
import pytest
from unittest.mock import Mock, patch

from core.repoe_tier_provider import (
    RePoETier,
    RePoETierProvider,
    BaseItemRecommendation,
    BaseItemRecommender,
    get_repoe_tier_provider,
    get_base_item_recommender,
    STAT_ID_MAPPING,
    EXCLUDE_MOD_GROUPS,
    EXCLUDE_MOD_ID_PATTERNS,
    ITEM_CLASS_TO_SLOT,
)


class TestRePoETier:
    """Tests for RePoETier dataclass."""

    def test_basic_creation(self):
        """Test creating a basic RePoETier."""
        tier = RePoETier(
            stat_type="life",
            tier_number=1,
            mod_name="of the Godslayer",
            mod_id="LocalIncreasedLife1",
            ilvl_required=82,
            min_value=90,
            max_value=99,
            generation_type="prefix",
        )
        assert tier.stat_type == "life"
        assert tier.tier_number == 1
        assert tier.mod_name == "of the Godslayer"
        assert tier.ilvl_required == 82
        assert tier.min_value == 90
        assert tier.max_value == 99
        assert tier.generation_type == "prefix"

    def test_display_range_single_value(self):
        """Test display_range when min equals max."""
        tier = RePoETier(
            stat_type="strength",
            tier_number=1,
            mod_name="of the Titan",
            mod_id="StrengthMod1",
            ilvl_required=82,
            min_value=55,
            max_value=55,
            generation_type="suffix",
        )
        assert tier.display_range == "55"

    def test_display_range_range(self):
        """Test display_range with different min/max."""
        tier = RePoETier(
            stat_type="life",
            tier_number=2,
            mod_name="of the Leviathan",
            mod_id="LocalIncreasedLife2",
            ilvl_required=75,
            min_value=80,
            max_value=89,
            generation_type="prefix",
        )
        assert tier.display_range == "80-89"


class TestStatIdMapping:
    """Tests for stat ID mapping constants."""

    def test_common_stats_mapped(self):
        """Test that common stats have mappings."""
        common_stats = [
            "life", "energy_shield", "fire_resistance", "cold_resistance",
            "lightning_resistance", "chaos_resistance", "strength", "dexterity",
            "intelligence", "movement_speed", "attack_speed", "cast_speed",
        ]
        for stat in common_stats:
            assert stat in STAT_ID_MAPPING, f"{stat} should be in STAT_ID_MAPPING"

    def test_mapping_format(self):
        """Test that mappings have correct format."""
        for stat_type, mapping in STAT_ID_MAPPING.items():
            assert isinstance(mapping, tuple), f"{stat_type} mapping should be tuple"
            assert len(mapping) == 3, f"{stat_type} mapping should have 3 elements"
            repoe_id, gen_type, is_pct = mapping
            assert isinstance(repoe_id, str), f"{stat_type} repoe_id should be string"
            assert gen_type is None or gen_type in ("prefix", "suffix")
            assert isinstance(is_pct, bool)


class TestExcludePatterns:
    """Tests for mod exclusion patterns."""

    def test_exclude_mod_groups(self):
        """Test exclude mod groups contains expected entries."""
        expected_groups = ["essence", "delve", "incursion", "synthesis", "influenced", "veiled", "crafted"]
        for group in expected_groups:
            assert group in EXCLUDE_MOD_GROUPS

    def test_exclude_mod_id_patterns(self):
        """Test exclude mod ID patterns contains expected entries."""
        expected_patterns = ["essence", "hunter", "redeemer", "crusader", "warlord", "shaper", "elder"]
        for pattern in expected_patterns:
            assert pattern in EXCLUDE_MOD_ID_PATTERNS


class TestRePoETierProvider:
    """Tests for RePoETierProvider class."""

    def test_initialization_default(self):
        """Test default initialization creates client."""
        with patch('core.repoe_tier_provider.RePoEClient') as MockClient:
            mock_client = Mock()
            MockClient.return_value = mock_client

            provider = RePoETierProvider()
            assert provider._client is not None
            assert provider._tier_cache == {}
            assert provider._mods_data is None

    def test_initialization_with_client(self):
        """Test initialization with provided client."""
        mock_client = Mock()
        provider = RePoETierProvider(repoe_client=mock_client)
        assert provider._client is mock_client

    def test_get_mods_caches(self):
        """Test _get_mods caches result."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {"mod1": {"name": "Test"}}

        provider = RePoETierProvider(repoe_client=mock_client)

        # First call
        mods1 = provider._get_mods()
        # Second call
        mods2 = provider._get_mods()

        # Should only call get_mods once
        assert mock_client.get_mods.call_count == 1
        assert mods1 is mods2

    def test_is_standard_mod_non_item_domain(self):
        """Test _is_standard_mod rejects non-item domain."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {"domain": "flask", "generation_type": "prefix"}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_non_prefix_suffix(self):
        """Test _is_standard_mod rejects non-prefix/suffix."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {"domain": "item", "generation_type": "unique"}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_essence_only(self):
        """Test _is_standard_mod rejects essence-only mods."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {"domain": "item", "generation_type": "prefix", "is_essence_only": True}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_excluded_group(self):
        """Test _is_standard_mod rejects excluded groups."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {"domain": "item", "generation_type": "prefix", "groups": ["Essence"]}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_excluded_mod_id(self):
        """Test _is_standard_mod rejects excluded mod IDs."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {"domain": "item", "generation_type": "prefix", "groups": []}
        assert provider._is_standard_mod(mod_info, mod_id="ShaperMod1") is False
        assert provider._is_standard_mod(mod_info, mod_id="HunterLife1") is False

    def test_is_standard_mod_excluded_mod_name(self):
        """Test _is_standard_mod rejects excluded mod names."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {"domain": "item", "generation_type": "prefix", "groups": [], "name": "Hunter's Strike"}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_valid(self):
        """Test _is_standard_mod accepts valid standard mod."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {
            "domain": "item",
            "generation_type": "prefix",
            "groups": ["Life"],
            "name": "Robust",
        }
        assert provider._is_standard_mod(mod_info, mod_id="IncreasedLife1") is True

    def test_has_positive_spawn_weight_weapon_only(self):
        """Test _has_positive_spawn_weight rejects weapon-only mods."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {
            "spawn_weights": [
                {"tag": "sword", "weight": 1000},
                {"tag": "axe", "weight": 1000},
            ]
        }
        assert provider._has_positive_spawn_weight(mod_info, exclude_weapon_only=True) is False

    def test_has_positive_spawn_weight_armor(self):
        """Test _has_positive_spawn_weight accepts armor mods."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {
            "spawn_weights": [
                {"tag": "helmet", "weight": 1000},
                {"tag": "body_armour", "weight": 1000},
            ]
        }
        assert provider._has_positive_spawn_weight(mod_info) is True

    def test_has_positive_spawn_weight_jewelry(self):
        """Test _has_positive_spawn_weight accepts jewelry mods."""
        provider = RePoETierProvider(repoe_client=Mock())

        mod_info = {
            "spawn_weights": [
                {"tag": "ring", "weight": 1000},
                {"tag": "amulet", "weight": 1000},
            ]
        }
        assert provider._has_positive_spawn_weight(mod_info) is True

    def test_get_tiers_for_stat_unknown(self):
        """Test get_tiers_for_stat with unknown stat type."""
        provider = RePoETierProvider(repoe_client=Mock())

        result = provider.get_tiers_for_stat("unknown_stat_type")
        assert result == []

    def test_get_tiers_for_stat_caches(self):
        """Test get_tiers_for_stat caches results."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {}

        provider = RePoETierProvider(repoe_client=mock_client)

        # Pre-populate cache
        cached_tiers = [
            RePoETier("life", 1, "T1", "mod1", 82, 90, 99, "prefix")
        ]
        provider._tier_cache["life"] = cached_tiers

        result = provider.get_tiers_for_stat("life")
        assert result == cached_tiers
        # Should not call get_mods since cached
        mock_client.get_mods.assert_not_called()

    def test_get_tiers_for_stat_force_refresh(self):
        """Test get_tiers_for_stat with force_refresh."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {}

        provider = RePoETierProvider(repoe_client=mock_client)

        # Pre-populate cache
        provider._tier_cache["life"] = [
            RePoETier("life", 1, "T1", "mod1", 82, 90, 99, "prefix")
        ]

        result = provider.get_tiers_for_stat("life", force_refresh=True)
        # Should call get_mods despite cache
        mock_client.get_mods.assert_called()

    def test_get_best_tier_for_ilvl(self):
        """Test get_best_tier_for_ilvl."""
        mock_client = Mock()

        provider = RePoETierProvider(repoe_client=mock_client)

        # Pre-populate cache
        provider._tier_cache["life"] = [
            RePoETier("life", 1, "T1", "mod1", 82, 90, 99, "prefix"),
            RePoETier("life", 2, "T2", "mod2", 75, 80, 89, "prefix"),
            RePoETier("life", 3, "T3", "mod3", 64, 70, 79, "prefix"),
        ]

        # ilvl 86 should get T1
        result = provider.get_best_tier_for_ilvl("life", 86)
        assert result.tier_number == 1

        # ilvl 75 should get T2
        result = provider.get_best_tier_for_ilvl("life", 75)
        assert result.tier_number == 2

        # ilvl 50 should get lowest tier
        result = provider.get_best_tier_for_ilvl("life", 50)
        assert result.tier_number == 3

    def test_get_best_tier_for_ilvl_no_tiers(self):
        """Test get_best_tier_for_ilvl with no tiers."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {}

        provider = RePoETierProvider(repoe_client=mock_client)

        result = provider.get_best_tier_for_ilvl("unknown_stat", 86)
        assert result is None

    def test_get_tier_data_tuple(self):
        """Test get_tier_data_tuple format."""
        mock_client = Mock()

        provider = RePoETierProvider(repoe_client=mock_client)

        # Pre-populate cache
        provider._tier_cache["life"] = [
            RePoETier("life", 1, "T1", "mod1", 82, 90, 99, "prefix"),
            RePoETier("life", 2, "T2", "mod2", 75, 80, 89, "prefix"),
        ]

        result = provider.get_tier_data_tuple("life")
        assert len(result) == 2
        assert result[0] == (1, 82, 90, 99)
        assert result[1] == (2, 75, 80, 89)

    def test_get_all_available_stats(self):
        """Test get_all_available_stats returns all mapped stats."""
        provider = RePoETierProvider(repoe_client=Mock())

        stats = provider.get_all_available_stats()
        assert len(stats) == len(STAT_ID_MAPPING)
        assert "life" in stats
        assert "fire_resistance" in stats

    def test_build_complete_tier_data(self):
        """Test build_complete_tier_data."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {}

        provider = RePoETierProvider(repoe_client=mock_client)

        # Pre-populate cache for a couple stats
        provider._tier_cache["life"] = [
            RePoETier("life", 1, "T1", "mod1", 82, 90, 99, "prefix"),
        ]
        provider._tier_cache["fire_resistance"] = [
            RePoETier("fire_resistance", 1, "T1", "mod1", 84, 46, 48, "suffix"),
        ]

        result = provider.build_complete_tier_data()
        assert "life" in result
        assert "fire_resistance" in result

    def test_clear_cache(self):
        """Test clear_cache clears all caches."""
        mock_client = Mock()
        provider = RePoETierProvider(repoe_client=mock_client)

        provider._tier_cache["life"] = []
        provider._mods_data = {"some": "data"}

        provider.clear_cache()

        assert provider._tier_cache == {}
        assert provider._mods_data is None


class TestBaseItemRecommendation:
    """Tests for BaseItemRecommendation dataclass."""

    def test_basic_creation(self):
        """Test creating a basic BaseItemRecommendation."""
        rec = BaseItemRecommendation(
            name="Vaal Regalia",
            item_class="Body Armour",
            drop_level=68,
            tags=["int_armour", "body_armour"],
            requirements={"Int": 194},
            defense_type="energy_shield",
        )
        assert rec.name == "Vaal Regalia"
        assert rec.item_class == "Body Armour"
        assert rec.drop_level == 68
        assert rec.defense_type == "energy_shield"


class TestBaseItemRecommender:
    """Tests for BaseItemRecommender class."""

    def test_initialization_default(self):
        """Test default initialization creates client."""
        with patch('core.repoe_tier_provider.RePoEClient') as MockClient:
            mock_client = Mock()
            MockClient.return_value = mock_client

            recommender = BaseItemRecommender()
            assert recommender._client is not None

    def test_initialization_with_client(self):
        """Test initialization with provided client."""
        mock_client = Mock()
        recommender = BaseItemRecommender(repoe_client=mock_client)
        assert recommender._client is mock_client

    def test_get_defense_type_str(self):
        """Test _get_defense_type for strength (armour)."""
        recommender = BaseItemRecommender(repoe_client=Mock())

        tags = ["str_armour", "body_armour"]
        result = recommender._get_defense_type(tags)
        assert result == "armour"

    def test_get_defense_type_dex(self):
        """Test _get_defense_type for dexterity (evasion)."""
        recommender = BaseItemRecommender(repoe_client=Mock())

        tags = ["dex_armour", "body_armour"]
        result = recommender._get_defense_type(tags)
        assert result == "evasion"

    def test_get_defense_type_int(self):
        """Test _get_defense_type for intelligence (ES)."""
        recommender = BaseItemRecommender(repoe_client=Mock())

        tags = ["int_armour", "body_armour"]
        result = recommender._get_defense_type(tags)
        assert result == "energy_shield"

    def test_get_defense_type_hybrid(self):
        """Test _get_defense_type for hybrid."""
        recommender = BaseItemRecommender(repoe_client=Mock())

        tags = ["str_int_armour", "body_armour"]
        result = recommender._get_defense_type(tags)
        assert result == "hybrid"

    def test_get_defense_type_unknown(self):
        """Test _get_defense_type for unknown tags."""
        recommender = BaseItemRecommender(repoe_client=Mock())

        tags = ["ring", "jewelry"]
        result = recommender._get_defense_type(tags)
        assert result == "unknown"

    def test_get_best_bases_for_slot(self):
        """Test get_best_bases_for_slot."""
        mock_client = Mock()
        mock_client.get_base_items.return_value = {
            "VaalRegalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {"Int": 194},
            },
            "AstralPlate": {
                "name": "Astral Plate",
                "item_class": "Body Armour",
                "drop_level": 62,
                "tags": ["str_armour"],
                "requirements": {"Str": 180},
            },
            "HubrisCirclet": {
                "name": "Hubris Circlet",
                "item_class": "Helmet",
                "drop_level": 69,
                "tags": ["int_armour"],
                "requirements": {"Int": 154},
            },
        }

        recommender = BaseItemRecommender(repoe_client=mock_client)

        # Get body armours
        results = recommender.get_best_bases_for_slot("Body Armour", min_drop_level=60)
        assert len(results) == 2
        # Should be sorted by drop level descending
        assert results[0].name == "Vaal Regalia"
        assert results[1].name == "Astral Plate"

    def test_get_best_bases_for_slot_filtered_by_defense(self):
        """Test get_best_bases_for_slot filtered by defense type."""
        mock_client = Mock()
        mock_client.get_base_items.return_value = {
            "VaalRegalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {"Int": 194},
            },
            "AstralPlate": {
                "name": "Astral Plate",
                "item_class": "Body Armour",
                "drop_level": 62,
                "tags": ["str_armour"],
                "requirements": {"Str": 180},
            },
        }

        recommender = BaseItemRecommender(repoe_client=mock_client)

        # Get ES body armours only
        results = recommender.get_best_bases_for_slot(
            "Body Armour",
            defense_type="energy_shield",
            min_drop_level=60
        )
        assert len(results) == 1
        assert results[0].name == "Vaal Regalia"

    def test_get_best_bases_for_slot_min_level(self):
        """Test get_best_bases_for_slot respects min_drop_level."""
        mock_client = Mock()
        mock_client.get_base_items.return_value = {
            "VaalRegalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {"Int": 194},
            },
            "SimpleRobe": {
                "name": "Simple Robe",
                "item_class": "Body Armour",
                "drop_level": 1,
                "tags": ["int_armour"],
                "requirements": {},
            },
        }

        recommender = BaseItemRecommender(repoe_client=mock_client)

        results = recommender.get_best_bases_for_slot("Body Armour", min_drop_level=60)
        assert len(results) == 1
        assert results[0].name == "Vaal Regalia"

    def test_get_recommended_base_es_build(self):
        """Test get_recommended_base for ES build."""
        mock_client = Mock()
        mock_client.get_base_items.return_value = {
            "VaalRegalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {"Int": 194},
            },
            "AstralPlate": {
                "name": "Astral Plate",
                "item_class": "Body Armour",
                "drop_level": 62,
                "tags": ["str_armour"],
                "requirements": {"Str": 180},
            },
        }

        recommender = BaseItemRecommender(repoe_client=mock_client)

        result = recommender.get_recommended_base("Body Armour", is_es_build=True)
        assert result is not None
        assert result.name == "Vaal Regalia"

    def test_get_recommended_base_armour_build(self):
        """Test get_recommended_base for armour build."""
        mock_client = Mock()
        mock_client.get_base_items.return_value = {
            "VaalRegalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {"Int": 194},
            },
            "AstralPlate": {
                "name": "Astral Plate",
                "item_class": "Body Armour",
                "drop_level": 62,
                "tags": ["str_armour"],
                "requirements": {"Str": 180},
            },
        }

        recommender = BaseItemRecommender(repoe_client=mock_client)

        result = recommender.get_recommended_base("Body Armour", is_armour_build=True)
        assert result is not None
        assert result.name == "Astral Plate"

    def test_get_recommended_base_no_matches(self):
        """Test get_recommended_base when no matches."""
        mock_client = Mock()
        mock_client.get_base_items.return_value = {}

        recommender = BaseItemRecommender(repoe_client=mock_client)

        result = recommender.get_recommended_base("Body Armour")
        assert result is None


class TestItemClassToSlotMapping:
    """Tests for item class to slot mapping."""

    def test_common_slots_mapped(self):
        """Test that common item classes are mapped."""
        expected = [
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Belt", "Ring", "Amulet", "Shield",
        ]
        for item_class in expected:
            assert item_class in ITEM_CLASS_TO_SLOT

    def test_quiver_mapped_to_shield(self):
        """Test quiver is treated like shield slot."""
        assert ITEM_CLASS_TO_SLOT.get("Quiver") == "Shield"


class TestSingletonGetters:
    """Tests for singleton getter functions."""

    def test_get_repoe_tier_provider(self):
        """Test get_repoe_tier_provider singleton."""
        import core.repoe_tier_provider as module
        module._provider_instance = None

        with patch.object(module, 'RePoETierProvider') as MockProvider:
            mock_instance = Mock()
            MockProvider.return_value = mock_instance

            provider1 = get_repoe_tier_provider()
            provider2 = get_repoe_tier_provider()

            # Should only create one instance
            MockProvider.assert_called_once()
            assert provider1 is provider2

    def test_get_base_item_recommender(self):
        """Test get_base_item_recommender singleton."""
        import core.repoe_tier_provider as module
        module._recommender_instance = None

        with patch.object(module, 'BaseItemRecommender') as MockRecommender:
            mock_instance = Mock()
            MockRecommender.return_value = mock_instance

            recommender1 = get_base_item_recommender()
            recommender2 = get_base_item_recommender()

            # Should only create one instance
            MockRecommender.assert_called_once()
            assert recommender1 is recommender2


class TestRePoETierProviderIntegration:
    """Integration tests with mocked RePoE data."""

    def test_extract_life_tiers(self):
        """Test extracting life tiers from mock mod data."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {
            "LocalIncreasedPhysicalDamageReductionRatingPercent1": {
                "domain": "item",
                "generation_type": "prefix",
                "groups": ["Armour"],
                "name": "Sturdy",
                "required_level": 1,
                "stats": [{"id": "local_physical_damage_reduction_rating_+%", "min": 10, "max": 20}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
            "IncreasedLife1": {
                "domain": "item",
                "generation_type": "prefix",
                "groups": ["Life"],
                "name": "Hale",
                "required_level": 1,
                "stats": [{"id": "base_maximum_life", "min": 10, "max": 19}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
            "IncreasedLife2": {
                "domain": "item",
                "generation_type": "prefix",
                "groups": ["Life"],
                "name": "Healthy",
                "required_level": 11,
                "stats": [{"id": "base_maximum_life", "min": 20, "max": 29}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
            "IncreasedLife3": {
                "domain": "item",
                "generation_type": "prefix",
                "groups": ["Life"],
                "name": "Sanguine",
                "required_level": 22,
                "stats": [{"id": "base_maximum_life", "min": 30, "max": 39}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
        }

        provider = RePoETierProvider(repoe_client=mock_client)

        tiers = provider.get_tiers_for_stat("life")

        # Should have 3 life tiers
        assert len(tiers) == 3
        # Sorted by ilvl descending (T1 first)
        assert tiers[0].mod_name == "Sanguine"
        assert tiers[0].tier_number == 1
        assert tiers[1].mod_name == "Healthy"
        assert tiers[2].mod_name == "Hale"

    def test_exclude_hybrid_mods(self):
        """Test that hybrid mods (multiple stats) are excluded."""
        mock_client = Mock()
        mock_client.get_mods.return_value = {
            "HybridLifeMana": {
                "domain": "item",
                "generation_type": "prefix",
                "groups": ["Life", "Mana"],
                "name": "Vivid",
                "required_level": 40,
                "stats": [
                    {"id": "base_maximum_life", "min": 40, "max": 49},
                    {"id": "base_maximum_mana", "min": 30, "max": 39},
                ],
                "spawn_weights": [{"tag": "body_armour", "weight": 500}],
            },
            "PureLife": {
                "domain": "item",
                "generation_type": "prefix",
                "groups": ["Life"],
                "name": "Robust",
                "required_level": 44,
                "stats": [{"id": "base_maximum_life", "min": 50, "max": 59}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
        }

        provider = RePoETierProvider(repoe_client=mock_client)

        tiers = provider.get_tiers_for_stat("life")

        # Should only have the pure life mod, not the hybrid
        assert len(tiers) == 1
        assert tiers[0].mod_name == "Robust"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
