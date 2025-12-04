"""Tests for core/tree_comparison.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestTreeComparisonResult:
    """Tests for TreeComparisonResult dataclass."""

    def test_creation(self):
        """Test creating TreeComparisonResult."""
        from core.tree_comparison import TreeComparisonResult

        result = TreeComparisonResult(
            similarity_percent=85.5,
            shared_count=100,
            missing_count=10,
            extra_count=5,
            shared_nodes=[1, 2, 3],
            missing_nodes=[4, 5],
            extra_nodes=[6],
            missing_masteries=[(100, 1)],
            your_build_name="My Build",
            target_build_name="Guide Build",
            your_node_count=105,
            target_node_count=110,
        )

        assert result.similarity_percent == 85.5
        assert result.shared_count == 100
        assert result.missing_count == 10
        assert result.extra_count == 5
        assert result.shared_nodes == [1, 2, 3]
        assert result.missing_nodes == [4, 5]
        assert result.extra_nodes == [6]
        assert result.missing_masteries == [(100, 1)]
        assert result.your_build_name == "My Build"
        assert result.target_build_name == "Guide Build"
        assert result.your_node_count == 105
        assert result.target_node_count == 110


class TestTreeComparisonServiceInit:
    """Tests for TreeComparisonService initialization."""

    def test_init_no_params(self):
        """Test initialization without parameters."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        assert service.character_manager is None
        assert service.parser is not None
        assert service.comparator is not None

    def test_init_with_character_manager(self):
        """Test initialization with character_manager."""
        from core.tree_comparison import TreeComparisonService

        mock_manager = MagicMock()
        service = TreeComparisonService(character_manager=mock_manager)

        assert service.character_manager is mock_manager


class TestTreeComparisonServiceComparePobCodes:
    """Tests for compare_pob_codes method."""

    def test_compare_pob_codes_success(self):
        """Test compare_pob_codes with valid codes."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        with patch('core.tree_comparison.PoBDecoder.decode_pob_code') as mock_decode:
            mock_decode.side_effect = ["<xml1>", "<xml2>"]

            with patch.object(service, '_compare_xml') as mock_compare:
                mock_result = MagicMock()
                mock_compare.return_value = mock_result

                result = service.compare_pob_codes(
                    your_code="code1",
                    target_code="code2",
                    your_name="Build 1",
                    target_name="Build 2",
                )

                assert result is mock_result
                mock_compare.assert_called_once_with("<xml1>", "<xml2>", "Build 1", "Build 2")


class TestTreeComparisonServiceCompareProfileToCode:
    """Tests for compare_profile_to_code method."""

    def test_compare_profile_to_code_no_manager(self):
        """Test compare_profile_to_code without character_manager."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        with pytest.raises(ValueError, match="CharacterManager not available"):
            service.compare_profile_to_code("profile", "code")

    def test_compare_profile_to_code_profile_not_found(self):
        """Test compare_profile_to_code with non-existent profile."""
        from core.tree_comparison import TreeComparisonService

        mock_manager = MagicMock()
        mock_manager.get_profile.return_value = None

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="Profile not found"):
            service.compare_profile_to_code("nonexistent", "code")

    def test_compare_profile_to_code_no_pob_code(self):
        """Test compare_profile_to_code with profile missing pob_code."""
        from core.tree_comparison import TreeComparisonService

        mock_profile = MagicMock()
        mock_profile.pob_code = None

        mock_manager = MagicMock()
        mock_manager.get_profile.return_value = mock_profile

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="has no PoB code"):
            service.compare_profile_to_code("myprofile", "code")

    def test_compare_profile_to_code_success(self):
        """Test compare_profile_to_code with valid profile."""
        from core.tree_comparison import TreeComparisonService

        mock_profile = MagicMock()
        mock_profile.pob_code = "valid_pob_code"

        mock_manager = MagicMock()
        mock_manager.get_profile.return_value = mock_profile

        service = TreeComparisonService(character_manager=mock_manager)

        with patch.object(service, 'compare_pob_codes') as mock_compare:
            mock_result = MagicMock()
            mock_compare.return_value = mock_result

            result = service.compare_profile_to_code(
                "myprofile",
                "target_code",
                "Target Build"
            )

            assert result is mock_result
            mock_compare.assert_called_once_with(
                your_code="valid_pob_code",
                target_code="target_code",
                your_name="myprofile",
                target_name="Target Build",
            )


class TestTreeComparisonServiceCompareProfiles:
    """Tests for compare_profiles method."""

    def test_compare_profiles_no_manager(self):
        """Test compare_profiles without character_manager."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        with pytest.raises(ValueError, match="CharacterManager not available"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_your_profile_not_found(self):
        """Test compare_profiles with your profile not found."""
        from core.tree_comparison import TreeComparisonService

        mock_manager = MagicMock()
        mock_manager.get_profile.return_value = None

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="Profile not found.*profile1"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_target_profile_not_found(self):
        """Test compare_profiles with target profile not found."""
        from core.tree_comparison import TreeComparisonService

        mock_your_profile = MagicMock()

        mock_manager = MagicMock()
        mock_manager.get_profile.side_effect = [mock_your_profile, None]

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="Profile not found.*profile2"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_your_profile_no_code(self):
        """Test compare_profiles with your profile missing pob_code."""
        from core.tree_comparison import TreeComparisonService

        mock_your_profile = MagicMock()
        mock_your_profile.pob_code = None

        mock_target_profile = MagicMock()
        mock_target_profile.pob_code = "valid_code"

        mock_manager = MagicMock()
        mock_manager.get_profile.side_effect = [mock_your_profile, mock_target_profile]

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="profile1.*has no PoB code"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_target_profile_no_code(self):
        """Test compare_profiles with target profile missing pob_code."""
        from core.tree_comparison import TreeComparisonService

        mock_your_profile = MagicMock()
        mock_your_profile.pob_code = "valid_code"

        mock_target_profile = MagicMock()
        mock_target_profile.pob_code = None

        mock_manager = MagicMock()
        mock_manager.get_profile.side_effect = [mock_your_profile, mock_target_profile]

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="profile2.*has no PoB code"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_success(self):
        """Test compare_profiles with valid profiles."""
        from core.tree_comparison import TreeComparisonService

        mock_your_profile = MagicMock()
        mock_your_profile.pob_code = "code1"

        mock_target_profile = MagicMock()
        mock_target_profile.pob_code = "code2"

        mock_manager = MagicMock()
        mock_manager.get_profile.side_effect = [mock_your_profile, mock_target_profile]

        service = TreeComparisonService(character_manager=mock_manager)

        with patch.object(service, 'compare_pob_codes') as mock_compare:
            mock_result = MagicMock()
            mock_compare.return_value = mock_result

            result = service.compare_profiles("profile1", "profile2")

            assert result is mock_result
            mock_compare.assert_called_once_with(
                your_code="code1",
                target_code="code2",
                your_name="profile1",
                target_name="profile2",
            )


class TestTreeComparisonServiceCompareXmlWithSpecs:
    """Tests for compare_xml_with_specs method."""

    def test_compare_xml_with_specs(self):
        """Test compare_xml_with_specs delegates to _compare_xml."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        with patch.object(service, '_compare_xml') as mock_compare:
            mock_result = MagicMock()
            mock_compare.return_value = mock_result

            result = service.compare_xml_with_specs(
                your_xml="<xml1>",
                target_xml="<xml2>",
                your_name="Build 1",
                target_name="Build 2",
                your_spec_idx=1,
                target_spec_idx=2,
            )

            assert result is mock_result
            mock_compare.assert_called_once_with(
                "<xml1>", "<xml2>", "Build 1", "Build 2", 1, 2
            )


class TestTreeComparisonServiceCompareXml:
    """Tests for _compare_xml method."""

    def test_compare_xml_no_your_specs(self):
        """Test _compare_xml with no specs from your build."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()
        service.parser = MagicMock()
        service.parser.parse_tree_specs.side_effect = [[], [MagicMock()]]

        with pytest.raises(ValueError, match="Could not parse tree from your build"):
            service._compare_xml("<xml1>", "<xml2>", "Build 1", "Build 2")

    def test_compare_xml_no_target_specs(self):
        """Test _compare_xml with no specs from target build."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()
        service.parser = MagicMock()
        service.parser.parse_tree_specs.side_effect = [[MagicMock()], []]

        with pytest.raises(ValueError, match="Could not parse tree from target build"):
            service._compare_xml("<xml1>", "<xml2>", "Build 1", "Build 2")

    def test_compare_xml_success(self):
        """Test _compare_xml with valid specs."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        # Mock specs
        your_spec = MagicMock()
        your_spec.nodes = {1, 2, 3, 4, 5}
        your_spec.mastery_effects = {}

        target_spec = MagicMock()
        target_spec.nodes = {1, 2, 3, 6, 7}
        target_spec.mastery_effects = {}

        service.parser = MagicMock()
        service.parser.parse_tree_specs.side_effect = [[your_spec], [target_spec]]

        # Mock comparison result
        mock_delta = MagicMock()
        mock_delta.shared_nodes = [1, 2, 3]
        mock_delta.missing_nodes = [6, 7]
        mock_delta.extra_nodes = [4, 5]
        mock_delta.missing_masteries = []

        service.comparator = MagicMock()
        service.comparator.compare_trees.return_value = mock_delta

        result = service._compare_xml("<xml1>", "<xml2>", "Build 1", "Build 2")

        assert result.shared_count == 3
        assert result.missing_count == 2
        assert result.extra_count == 2
        assert result.your_build_name == "Build 1"
        assert result.target_build_name == "Build 2"
        assert result.your_node_count == 5
        assert result.target_node_count == 5

    def test_compare_xml_similarity_calculation(self):
        """Test _compare_xml similarity calculation."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        # 5 shared out of 7 unique = ~71.4%
        your_spec = MagicMock()
        your_spec.nodes = {1, 2, 3, 4, 5}
        your_spec.mastery_effects = {}

        target_spec = MagicMock()
        target_spec.nodes = {1, 2, 3, 4, 5, 6, 7}
        target_spec.mastery_effects = {}

        service.parser = MagicMock()
        service.parser.parse_tree_specs.side_effect = [[your_spec], [target_spec]]

        mock_delta = MagicMock()
        mock_delta.shared_nodes = [1, 2, 3, 4, 5]
        mock_delta.missing_nodes = [6, 7]
        mock_delta.extra_nodes = []
        mock_delta.missing_masteries = []

        service.comparator = MagicMock()
        service.comparator.compare_trees.return_value = mock_delta

        result = service._compare_xml("<xml1>", "<xml2>", "Build 1", "Build 2")

        # 5 shared / 7 unique = 71.4%
        assert abs(result.similarity_percent - 71.4) < 0.1

    def test_compare_xml_empty_trees(self):
        """Test _compare_xml with empty trees."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        your_spec = MagicMock()
        your_spec.nodes = set()
        your_spec.mastery_effects = {}

        target_spec = MagicMock()
        target_spec.nodes = set()
        target_spec.mastery_effects = {}

        service.parser = MagicMock()
        service.parser.parse_tree_specs.side_effect = [[your_spec], [target_spec]]

        mock_delta = MagicMock()
        mock_delta.shared_nodes = []
        mock_delta.missing_nodes = []
        mock_delta.extra_nodes = []
        mock_delta.missing_masteries = []

        service.comparator = MagicMock()
        service.comparator.compare_trees.return_value = mock_delta

        result = service._compare_xml("<xml1>", "<xml2>", "Build 1", "Build 2")

        # Empty trees = 100% similarity
        assert result.similarity_percent == 100.0

    def test_compare_xml_spec_idx_bounds(self):
        """Test _compare_xml handles spec index out of bounds."""
        from core.tree_comparison import TreeComparisonService

        service = TreeComparisonService()

        spec1 = MagicMock()
        spec1.nodes = {1}
        spec1.mastery_effects = {}

        spec2 = MagicMock()
        spec2.nodes = {2}
        spec2.mastery_effects = {}

        # Only one spec in each list
        service.parser = MagicMock()
        service.parser.parse_tree_specs.side_effect = [[spec1], [spec2]]

        mock_delta = MagicMock()
        mock_delta.shared_nodes = []
        mock_delta.missing_nodes = []
        mock_delta.extra_nodes = []
        mock_delta.missing_masteries = []

        service.comparator = MagicMock()
        service.comparator.compare_trees.return_value = mock_delta

        # Request spec index 5, but only 1 spec exists - should fall back to 0
        result = service._compare_xml("<xml1>", "<xml2>", "B1", "B2", 5, 5)

        # Should not raise, should use index 0
        assert result is not None


class TestTreeComparisonServiceFormatReport:
    """Tests for format_comparison_report method."""

    def test_format_comparison_report_basic(self):
        """Test format_comparison_report basic output."""
        from core.tree_comparison import TreeComparisonService, TreeComparisonResult

        service = TreeComparisonService()

        result = TreeComparisonResult(
            similarity_percent=85.0,
            shared_count=100,
            missing_count=10,
            extra_count=5,
            shared_nodes=[],
            missing_nodes=[],
            extra_nodes=[],
            missing_masteries=[],
            your_build_name="My Build",
            target_build_name="Guide Build",
            your_node_count=105,
            target_node_count=110,
        )

        report = service.format_comparison_report(result)

        assert "My Build" in report
        assert "Guide Build" in report
        assert "85.0%" in report
        assert "105 nodes" in report
        assert "110 nodes" in report
        assert "Shared nodes: 100" in report
        assert "missing: 10" in report
        assert "Extra nodes you have: 5" in report

    def test_format_comparison_report_with_masteries(self):
        """Test format_comparison_report with missing masteries."""
        from core.tree_comparison import TreeComparisonService, TreeComparisonResult

        service = TreeComparisonService()

        result = TreeComparisonResult(
            similarity_percent=90.0,
            shared_count=100,
            missing_count=5,
            extra_count=2,
            shared_nodes=[],
            missing_nodes=[],
            extra_nodes=[],
            missing_masteries=[(1, 2), (3, 4)],
            your_build_name="Build A",
            target_build_name="Build B",
            your_node_count=102,
            target_node_count=105,
        )

        report = service.format_comparison_report(result)

        assert "Missing masteries: 2" in report
