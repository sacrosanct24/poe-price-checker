"""Tests for core/repoe_tier_provider.py - RePoE Tier Data Provider."""

import pytest
from unittest.mock import Mock, patch

from core.repoe_tier_provider import (
    STAT_ID_MAPPING,
    STAT_ID_ALTERNATIVES,
    EXCLUDE_MOD_GROUPS,
    EXCLUDE_MOD_ID_PATTERNS,
    EXCLUDE_MOD_NAMES,
    RePoETier,
    RePoETierProvider,
    BaseItemRecommendation,
    BaseItemRecommender,
    ITEM_CLASS_TO_SLOT,
    get_repoe_tier_provider,
    get_base_item_recommender,
)


# ============================================================================
# Constants Tests
# ============================================================================

class TestStatIdMapping:
    """Tests for STAT_ID_MAPPING constant."""

    def test_life_mapping(self):
        """Life stat is mapped correctly."""
        assert "life" in STAT_ID_MAPPING
        stat_id, gen_type, is_pct = STAT_ID_MAPPING["life"]
        assert stat_id == "base_maximum_life"
        assert is_pct is False

    def test_fire_resistance_mapping(self):
        """Fire resistance is suffix and percentage."""
        assert "fire_resistance" in STAT_ID_MAPPING
        stat_id, gen_type, is_pct = STAT_ID_MAPPING["fire_resistance"]
        assert gen_type == "suffix"
        assert is_pct is True

    def test_movement_speed_mapping(self):
        """Movement speed is prefix (boots)."""
        assert "movement_speed" in STAT_ID_MAPPING
        stat_id, gen_type, is_pct = STAT_ID_MAPPING["movement_speed"]
        assert gen_type == "prefix"
        assert is_pct is True

    def test_all_attributes_mapping(self):
        """All attributes mapping exists."""
        assert "all_attributes" in STAT_ID_MAPPING
        stat_id, gen_type, is_pct = STAT_ID_MAPPING["all_attributes"]
        assert stat_id == "additional_all_attributes"
        assert gen_type == "suffix"

    def test_common_stats_present(self):
        """Common stats have mappings."""
        expected_stats = [
            "life", "energy_shield", "armour", "evasion",
            "fire_resistance", "cold_resistance", "lightning_resistance", "chaos_resistance",
            "strength", "dexterity", "intelligence",
            "movement_speed", "attack_speed", "cast_speed",
            "critical_strike_chance", "critical_strike_multiplier",
            "mana", "accuracy",
        ]
        for stat in expected_stats:
            assert stat in STAT_ID_MAPPING, f"Missing mapping for {stat}"


class TestStatIdAlternatives:
    """Tests for STAT_ID_ALTERNATIVES constant."""

    def test_energy_shield_alternative(self):
        """Energy shield has alternative stat ID."""
        assert "energy_shield" in STAT_ID_ALTERNATIVES
        assert "base_maximum_energy_shield" in STAT_ID_ALTERNATIVES["energy_shield"]

    def test_armour_alternative(self):
        """Armour has alternative stat ID."""
        assert "armour" in STAT_ID_ALTERNATIVES

    def test_attack_speed_alternatives(self):
        """Attack speed has multiple alternatives."""
        assert "attack_speed" in STAT_ID_ALTERNATIVES
        alts = STAT_ID_ALTERNATIVES["attack_speed"]
        assert "local_attack_speed_+%" in alts


class TestExcludePatterns:
    """Tests for exclude patterns."""

    def test_exclude_mod_groups(self):
        """Exclude mod groups contains expected entries."""
        assert "essence" in EXCLUDE_MOD_GROUPS
        assert "delve" in EXCLUDE_MOD_GROUPS
        assert "incursion" in EXCLUDE_MOD_GROUPS
        assert "influenced" in EXCLUDE_MOD_GROUPS

    def test_exclude_mod_id_patterns(self):
        """Exclude patterns contains influence names."""
        assert "hunter" in EXCLUDE_MOD_ID_PATTERNS
        assert "shaper" in EXCLUDE_MOD_ID_PATTERNS
        assert "elder" in EXCLUDE_MOD_ID_PATTERNS
        assert "essence" in EXCLUDE_MOD_ID_PATTERNS

    def test_exclude_mod_names(self):
        """Exclude names contains influenced prefixes."""
        assert "Hunter's" in EXCLUDE_MOD_NAMES
        assert "of the Elder" in EXCLUDE_MOD_NAMES
        assert "Elevated" in EXCLUDE_MOD_NAMES


class TestItemClassToSlot:
    """Tests for ITEM_CLASS_TO_SLOT mapping."""

    def test_armor_slots(self):
        """Armor slots are mapped correctly."""
        assert ITEM_CLASS_TO_SLOT["Helmet"] == "Helmet"
        assert ITEM_CLASS_TO_SLOT["Body Armour"] == "Body Armour"
        assert ITEM_CLASS_TO_SLOT["Gloves"] == "Gloves"
        assert ITEM_CLASS_TO_SLOT["Boots"] == "Boots"

    def test_jewelry_slots(self):
        """Jewelry slots are mapped correctly."""
        assert ITEM_CLASS_TO_SLOT["Belt"] == "Belt"
        assert ITEM_CLASS_TO_SLOT["Ring"] == "Ring"
        assert ITEM_CLASS_TO_SLOT["Amulet"] == "Amulet"

    def test_quiver_treated_as_shield(self):
        """Quiver is treated as shield slot."""
        assert ITEM_CLASS_TO_SLOT["Quiver"] == "Shield"


# ============================================================================
# RePoETier Dataclass Tests
# ============================================================================

class TestRePoETier:
    """Tests for RePoETier dataclass."""

    def test_basic_creation(self):
        """Create basic tier."""
        tier = RePoETier(
            stat_type="life",
            tier_number=1,
            mod_name="Peerless",
            mod_id="Life1",
            ilvl_required=86,
            min_value=90,
            max_value=99,
            generation_type="prefix",
        )

        assert tier.stat_type == "life"
        assert tier.tier_number == 1
        assert tier.mod_name == "Peerless"
        assert tier.ilvl_required == 86
        assert tier.min_value == 90
        assert tier.max_value == 99
        assert tier.generation_type == "prefix"

    def test_display_range_different_values(self):
        """display_range shows min-max when different."""
        tier = RePoETier(
            stat_type="life",
            tier_number=1,
            mod_name="Test",
            mod_id="test",
            ilvl_required=80,
            min_value=90,
            max_value=99,
            generation_type="prefix",
        )

        assert tier.display_range == "90-99"

    def test_display_range_same_values(self):
        """display_range shows single value when min=max."""
        tier = RePoETier(
            stat_type="fire_res",
            tier_number=1,
            mod_name="Test",
            mod_id="test",
            ilvl_required=80,
            min_value=46,
            max_value=46,
            generation_type="suffix",
        )

        assert tier.display_range == "46"


# ============================================================================
# RePoETierProvider Tests
# ============================================================================

class TestRePoETierProvider:
    """Tests for RePoETierProvider class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock RePoE client."""
        return Mock()

    @pytest.fixture
    def provider(self, mock_client):
        """Create provider with mock client."""
        return RePoETierProvider(repoe_client=mock_client)

    def test_init_with_client(self, provider, mock_client):
        """Initializes with provided client."""
        assert provider._client is mock_client
        assert provider._tier_cache == {}
        assert provider._mods_data is None

    def test_init_creates_client(self):
        """Creates client if not provided."""
        with patch('core.repoe_tier_provider.RePoEClient') as MockClient:
            RePoETierProvider()
            MockClient.assert_called_once()

    def test_get_mods_caches_data(self, provider, mock_client):
        """_get_mods caches data after first call."""
        mock_client.get_mods.return_value = {"mod1": {}}

        result1 = provider._get_mods()
        result2 = provider._get_mods()

        # Only called once due to caching
        mock_client.get_mods.assert_called_once()
        assert result1 == result2

    def test_get_mods_handles_none(self, provider, mock_client):
        """_get_mods handles None response."""
        mock_client.get_mods.return_value = None

        result = provider._get_mods()

        assert result == {}

    def test_is_standard_mod_requires_item_domain(self, provider):
        """_is_standard_mod rejects non-item domain."""
        mod_info = {'domain': 'crafted', 'generation_type': 'prefix'}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_requires_prefix_or_suffix(self, provider):
        """_is_standard_mod requires prefix or suffix generation type."""
        mod_info = {'domain': 'item', 'generation_type': 'corrupted'}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_rejects_essence_only(self, provider):
        """_is_standard_mod rejects essence-only mods."""
        mod_info = {'domain': 'item', 'generation_type': 'prefix', 'is_essence_only': True}
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_rejects_excluded_groups(self, provider):
        """_is_standard_mod rejects mods with excluded groups."""
        mod_info = {
            'domain': 'item',
            'generation_type': 'prefix',
            'groups': ['EssenceLifeModifier'],
        }
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_rejects_excluded_id_patterns(self, provider):
        """_is_standard_mod rejects mods with excluded ID patterns."""
        mod_info = {
            'domain': 'item',
            'generation_type': 'suffix',
        }
        assert provider._is_standard_mod(mod_info, mod_id="HunterFireResistance") is False

    def test_is_standard_mod_rejects_excluded_names(self, provider):
        """_is_standard_mod rejects mods with excluded names."""
        mod_info = {
            'domain': 'item',
            'generation_type': 'prefix',
            'name': "Hunter's Fortitude",
        }
        assert provider._is_standard_mod(mod_info) is False

    def test_is_standard_mod_accepts_valid_mod(self, provider):
        """_is_standard_mod accepts valid standard mod."""
        mod_info = {
            'domain': 'item',
            'generation_type': 'prefix',
            'groups': ['Life'],
            'name': 'Hale',
        }
        assert provider._is_standard_mod(mod_info, mod_id="LocalBaseLife1") is True

    def test_has_positive_spawn_weight_armor(self, provider):
        """_has_positive_spawn_weight detects armor spawn weights."""
        mod_info = {
            'spawn_weights': [
                {'tag': 'helmet', 'weight': 1000},
            ]
        }
        assert provider._has_positive_spawn_weight(mod_info) is True

    def test_has_positive_spawn_weight_rejects_weapon_only(self, provider):
        """_has_positive_spawn_weight rejects weapon-only mods."""
        mod_info = {
            'spawn_weights': [
                {'tag': 'sword', 'weight': 1000},
                {'tag': 'helmet', 'weight': 0},
            ]
        }
        assert provider._has_positive_spawn_weight(mod_info) is False

    def test_has_positive_spawn_weight_accepts_mixed(self, provider):
        """_has_positive_spawn_weight accepts weapon+armor mods."""
        mod_info = {
            'spawn_weights': [
                {'tag': 'sword', 'weight': 1000},
                {'tag': 'helmet', 'weight': 500},
            ]
        }
        assert provider._has_positive_spawn_weight(mod_info) is True

    def test_has_positive_spawn_weight_no_weight(self, provider):
        """_has_positive_spawn_weight returns False for no weights."""
        mod_info = {'spawn_weights': []}
        assert provider._has_positive_spawn_weight(mod_info) is False

    def test_get_tiers_for_stat_unknown_stat(self, provider):
        """get_tiers_for_stat returns empty for unknown stat."""
        result = provider.get_tiers_for_stat("unknown_stat_type")
        assert result == []

    def test_get_tiers_for_stat_uses_cache(self, provider, mock_client):
        """get_tiers_for_stat uses cached results."""
        mock_client.get_mods.return_value = {}
        provider._tier_cache["life"] = [Mock()]

        result = provider.get_tiers_for_stat("life")

        # Should use cache, not call get_mods
        mock_client.get_mods.assert_not_called()
        assert len(result) == 1

    def test_get_tiers_for_stat_force_refresh(self, provider, mock_client):
        """get_tiers_for_stat ignores cache with force_refresh."""
        mock_client.get_mods.return_value = {}
        provider._tier_cache["life"] = [Mock()]

        result = provider.get_tiers_for_stat("life", force_refresh=True)

        # Should call get_mods despite cache
        mock_client.get_mods.assert_called()
        assert result == []  # No matching mods in empty response

    def test_get_best_tier_for_ilvl_returns_best(self, provider):
        """get_best_tier_for_ilvl returns best tier for ilvl."""
        t1 = RePoETier("life", 1, "T1", "id1", 86, 90, 99, "prefix")
        t2 = RePoETier("life", 2, "T2", "id2", 75, 80, 89, "prefix")
        t3 = RePoETier("life", 3, "T3", "id3", 64, 70, 79, "prefix")
        provider._tier_cache["life"] = [t1, t2, t3]

        # ilvl 86 can get T1
        result = provider.get_best_tier_for_ilvl("life", 86)
        assert result.tier_number == 1

        # ilvl 75 can get T2
        result = provider.get_best_tier_for_ilvl("life", 75)
        assert result.tier_number == 2

        # ilvl 64 can get T3
        result = provider.get_best_tier_for_ilvl("life", 64)
        assert result.tier_number == 3

    def test_get_best_tier_for_ilvl_returns_lowest_for_low_ilvl(self, provider):
        """get_best_tier_for_ilvl returns lowest tier for very low ilvl."""
        t1 = RePoETier("life", 1, "T1", "id1", 86, 90, 99, "prefix")
        t2 = RePoETier("life", 2, "T2", "id2", 75, 80, 89, "prefix")
        provider._tier_cache["life"] = [t1, t2]

        result = provider.get_best_tier_for_ilvl("life", 50)

        # Should return T2 (lowest) since ilvl 50 can't get either
        assert result.tier_number == 2

    def test_get_best_tier_for_ilvl_returns_none_for_unknown(self, provider):
        """get_best_tier_for_ilvl returns None for unknown stat."""
        provider._tier_cache["life"] = []

        result = provider.get_best_tier_for_ilvl("life", 86)

        assert result is None

    def test_get_tier_data_tuple(self, provider):
        """get_tier_data_tuple returns correct format."""
        t1 = RePoETier("life", 1, "T1", "id1", 86, 90, 99, "prefix")
        t2 = RePoETier("life", 2, "T2", "id2", 75, 80, 89, "prefix")
        provider._tier_cache["life"] = [t1, t2]

        result = provider.get_tier_data_tuple("life")

        assert result == [
            (1, 86, 90, 99),
            (2, 75, 80, 89),
        ]

    def test_get_all_available_stats(self, provider):
        """get_all_available_stats returns all mapped stats."""
        result = provider.get_all_available_stats()

        assert "life" in result
        assert "fire_resistance" in result
        assert "movement_speed" in result
        assert len(result) == len(STAT_ID_MAPPING)

    def test_build_complete_tier_data(self, provider, mock_client):
        """build_complete_tier_data builds dict for all stats."""
        # Empty mods data - will result in no tiers
        mock_client.get_mods.return_value = {}

        result = provider.build_complete_tier_data()

        # Should be dict (possibly empty)
        assert isinstance(result, dict)

    def test_clear_cache(self, provider):
        """clear_cache clears both caches."""
        provider._tier_cache["life"] = [Mock()]
        provider._mods_data = {"some": "data"}

        provider.clear_cache()

        assert provider._tier_cache == {}
        assert provider._mods_data is None


# ============================================================================
# BaseItemRecommendation Tests
# ============================================================================

class TestBaseItemRecommendation:
    """Tests for BaseItemRecommendation dataclass."""

    def test_creation(self):
        """Create recommendation."""
        rec = BaseItemRecommendation(
            name="Vaal Regalia",
            item_class="Body Armour",
            drop_level=68,
            tags=["int_armour", "body_armour"],
            requirements={"int": 194},
            defense_type="energy_shield",
        )

        assert rec.name == "Vaal Regalia"
        assert rec.item_class == "Body Armour"
        assert rec.drop_level == 68
        assert rec.defense_type == "energy_shield"


# ============================================================================
# BaseItemRecommender Tests
# ============================================================================

class TestBaseItemRecommender:
    """Tests for BaseItemRecommender class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock RePoE client."""
        return Mock()

    @pytest.fixture
    def recommender(self, mock_client):
        """Create recommender with mock client."""
        return BaseItemRecommender(repoe_client=mock_client)

    def test_init_with_client(self, recommender, mock_client):
        """Initializes with provided client."""
        assert recommender._client is mock_client
        assert recommender._base_items is None

    def test_init_creates_client(self):
        """Creates client if not provided."""
        # BaseItemRecommender imports RePoEClient inside __init__ from data_sources
        with patch('data_sources.repoe_client.RePoEClient') as MockClient:
            BaseItemRecommender()
            MockClient.assert_called_once()

    def test_get_base_items_caches(self, recommender, mock_client):
        """_get_base_items caches results."""
        mock_client.get_base_items.return_value = {"item1": {}}

        result1 = recommender._get_base_items()
        result2 = recommender._get_base_items()

        mock_client.get_base_items.assert_called_once()
        assert result1 == result2

    def test_get_defense_type_armour(self, recommender):
        """_get_defense_type identifies armour."""
        tags = ["str_armour", "body_armour"]
        assert recommender._get_defense_type(tags) == "armour"

    def test_get_defense_type_evasion(self, recommender):
        """_get_defense_type identifies evasion."""
        tags = ["dex_armour", "body_armour"]
        assert recommender._get_defense_type(tags) == "evasion"

    def test_get_defense_type_energy_shield(self, recommender):
        """_get_defense_type identifies energy shield."""
        tags = ["int_armour", "body_armour"]
        assert recommender._get_defense_type(tags) == "energy_shield"

    def test_get_defense_type_hybrid(self, recommender):
        """_get_defense_type identifies hybrid."""
        tags = ["str_int_armour", "body_armour"]
        assert recommender._get_defense_type(tags) == "hybrid"

        tags = ["str_armour", "dex_armour"]
        assert recommender._get_defense_type(tags) == "hybrid"

    def test_get_defense_type_unknown(self, recommender):
        """_get_defense_type returns unknown for unrecognized tags."""
        tags = ["belt", "default"]
        assert recommender._get_defense_type(tags) == "unknown"

    def test_get_best_bases_for_slot(self, recommender, mock_client):
        """get_best_bases_for_slot returns matching bases."""
        mock_client.get_base_items.return_value = {
            "vaal_regalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {"int": 194},
            },
            "glorious_plate": {
                "name": "Glorious Plate",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["str_armour"],
                "requirements": {"str": 191},
            },
            "iron_ring": {
                "name": "Iron Ring",
                "item_class": "Ring",
                "drop_level": 1,
                "tags": ["ring"],
                "requirements": {},
            },
        }

        result = recommender.get_best_bases_for_slot("Body Armour", min_drop_level=60)

        assert len(result) == 2
        assert all(r.item_class == "Body Armour" for r in result)

    def test_get_best_bases_for_slot_filters_defense_type(self, recommender, mock_client):
        """get_best_bases_for_slot filters by defense type."""
        mock_client.get_base_items.return_value = {
            "vaal_regalia": {
                "name": "Vaal Regalia",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {},
            },
            "glorious_plate": {
                "name": "Glorious Plate",
                "item_class": "Body Armour",
                "drop_level": 68,
                "tags": ["str_armour"],
                "requirements": {},
            },
        }

        result = recommender.get_best_bases_for_slot(
            "Body Armour",
            defense_type="energy_shield",
            min_drop_level=60
        )

        assert len(result) == 1
        assert result[0].name == "Vaal Regalia"

    def test_get_best_bases_for_slot_filters_drop_level(self, recommender, mock_client):
        """get_best_bases_for_slot filters by min drop level."""
        mock_client.get_base_items.return_value = {
            "high_base": {
                "name": "High Base",
                "item_class": "Helmet",
                "drop_level": 84,
                "tags": ["str_armour"],
                "requirements": {},
            },
            "low_base": {
                "name": "Low Base",
                "item_class": "Helmet",
                "drop_level": 20,
                "tags": ["str_armour"],
                "requirements": {},
            },
        }

        result = recommender.get_best_bases_for_slot("Helmet", min_drop_level=60)

        assert len(result) == 1
        assert result[0].name == "High Base"

    def test_get_best_bases_for_slot_sorted_by_drop_level(self, recommender, mock_client):
        """get_best_bases_for_slot sorts by drop level descending."""
        mock_client.get_base_items.return_value = {
            "base_68": {
                "name": "Base 68",
                "item_class": "Boots",
                "drop_level": 68,
                "tags": ["str_armour"],
                "requirements": {},
            },
            "base_84": {
                "name": "Base 84",
                "item_class": "Boots",
                "drop_level": 84,
                "tags": ["str_armour"],
                "requirements": {},
            },
            "base_72": {
                "name": "Base 72",
                "item_class": "Boots",
                "drop_level": 72,
                "tags": ["str_armour"],
                "requirements": {},
            },
        }

        result = recommender.get_best_bases_for_slot("Boots", min_drop_level=60)

        assert result[0].drop_level == 84
        assert result[1].drop_level == 72
        assert result[2].drop_level == 68

    def test_get_recommended_base_es_build(self, recommender, mock_client):
        """get_recommended_base returns ES base for ES build."""
        mock_client.get_base_items.return_value = {
            "es_base": {
                "name": "ES Base",
                "item_class": "Helmet",
                "drop_level": 68,
                "tags": ["int_armour"],
                "requirements": {},
            },
            "armour_base": {
                "name": "Armour Base",
                "item_class": "Helmet",
                "drop_level": 68,
                "tags": ["str_armour"],
                "requirements": {},
            },
        }

        result = recommender.get_recommended_base("Helmet", is_es_build=True)

        assert result is not None
        assert result.name == "ES Base"

    def test_get_recommended_base_evasion_build(self, recommender, mock_client):
        """get_recommended_base returns evasion base for evasion build."""
        mock_client.get_base_items.return_value = {
            "evasion_base": {
                "name": "Evasion Base",
                "item_class": "Gloves",
                "drop_level": 68,
                "tags": ["dex_armour"],
                "requirements": {},
            },
        }

        result = recommender.get_recommended_base("Gloves", is_evasion_build=True)

        assert result is not None
        assert result.defense_type == "evasion"

    def test_get_recommended_base_returns_none(self, recommender, mock_client):
        """get_recommended_base returns None when no match."""
        mock_client.get_base_items.return_value = {}

        result = recommender.get_recommended_base("Belt")

        assert result is None


# ============================================================================
# Singleton Function Tests
# ============================================================================

class TestSingletonFunctions:
    """Tests for singleton functions."""

    def test_get_repoe_tier_provider_returns_same_instance(self):
        """get_repoe_tier_provider returns singleton."""
        import core.repoe_tier_provider as module
        original = module._provider_instance
        module._provider_instance = None

        try:
            with patch.object(RePoETierProvider, '__init__', return_value=None):
                provider1 = get_repoe_tier_provider()
                provider2 = get_repoe_tier_provider()

                assert provider1 is provider2
        finally:
            module._provider_instance = original

    def test_get_base_item_recommender_returns_same_instance(self):
        """get_base_item_recommender returns singleton."""
        import core.repoe_tier_provider as module
        original = module._recommender_instance
        module._recommender_instance = None

        try:
            with patch.object(BaseItemRecommender, '__init__', return_value=None):
                rec1 = get_base_item_recommender()
                rec2 = get_base_item_recommender()

                assert rec1 is rec2
        finally:
            module._recommender_instance = original


# ============================================================================
# Integration-style Tests (with mock data)
# ============================================================================

class TestTierProviderIntegration:
    """Integration tests with realistic mock data."""

    @pytest.fixture
    def realistic_mods(self):
        """Realistic mod data structure."""
        return {
            "LocalBaseLife1": {
                "domain": "item",
                "generation_type": "prefix",
                "name": "Peerless",
                "groups": ["Life"],
                "required_level": 86,
                "stats": [{"id": "base_maximum_life", "min": 90, "max": 99}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
            "LocalBaseLife2": {
                "domain": "item",
                "generation_type": "prefix",
                "name": "Prime",
                "groups": ["Life"],
                "required_level": 75,
                "stats": [{"id": "base_maximum_life", "min": 80, "max": 89}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
            "HunterLife": {
                "domain": "item",
                "generation_type": "prefix",
                "name": "Hunter's Vitality",
                "groups": ["Life"],
                "required_level": 86,
                "stats": [{"id": "base_maximum_life", "min": 95, "max": 110}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
            "EssenceLife": {
                "domain": "item",
                "generation_type": "prefix",
                "name": "Essences",
                "groups": ["Life", "EssenceModifier"],
                "is_essence_only": True,
                "required_level": 86,
                "stats": [{"id": "base_maximum_life", "min": 100, "max": 110}],
                "spawn_weights": [{"tag": "body_armour", "weight": 1000}],
            },
        }

    def test_filters_influenced_and_essence_mods(self, realistic_mods):
        """Provider filters out influenced and essence mods."""
        mock_client = Mock()
        mock_client.get_mods.return_value = realistic_mods

        provider = RePoETierProvider(repoe_client=mock_client)
        tiers = provider.get_tiers_for_stat("life")

        # Should only have 2 tiers (standard ones, not hunter or essence)
        assert len(tiers) == 2
        tier_names = [t.mod_name for t in tiers]
        assert "Peerless" in tier_names
        assert "Prime" in tier_names
        assert "Hunter's Vitality" not in tier_names
        assert "Essences" not in tier_names
