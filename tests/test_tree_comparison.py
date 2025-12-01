"""
Tests for Tree Comparison Service.

Tests the tree comparison functionality including:
- TreeComparisonResult dataclass
- TreeComparisonService methods
- Report formatting
"""
import pytest
from unittest.mock import Mock, patch

from core.tree_comparison import (
    TreeComparisonResult,
    TreeComparisonService,
)


class TestTreeComparisonResult:
    """Tests for TreeComparisonResult dataclass."""

    def test_basic_creation(self):
        """Test creating a basic result."""
        result = TreeComparisonResult(
            similarity_percent=75.5,
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
        assert result.similarity_percent == 75.5
        assert result.shared_count == 100
        assert result.missing_count == 10
        assert result.extra_count == 5
        assert len(result.shared_nodes) == 3
        assert len(result.missing_nodes) == 2
        assert len(result.extra_nodes) == 1
        assert len(result.missing_masteries) == 1
        assert result.your_build_name == "My Build"
        assert result.target_build_name == "Guide Build"
        assert result.your_node_count == 105
        assert result.target_node_count == 110

    def test_empty_nodes(self):
        """Test result with no differences."""
        result = TreeComparisonResult(
            similarity_percent=100.0,
            shared_count=100,
            missing_count=0,
            extra_count=0,
            shared_nodes=list(range(100)),
            missing_nodes=[],
            extra_nodes=[],
            missing_masteries=[],
            your_build_name="Build A",
            target_build_name="Build B",
            your_node_count=100,
            target_node_count=100,
        )
        assert result.similarity_percent == 100.0
        assert result.missing_count == 0
        assert result.extra_count == 0


class TestTreeComparisonService:
    """Tests for TreeComparisonService class."""

    def test_initialization_without_manager(self):
        """Test service initializes without character manager."""
        service = TreeComparisonService()
        assert service.character_manager is None
        assert service.parser is not None
        assert service.comparator is not None

    def test_initialization_with_manager(self):
        """Test service initializes with character manager."""
        mock_manager = Mock()
        service = TreeComparisonService(character_manager=mock_manager)
        assert service.character_manager is mock_manager

    @patch.object(TreeComparisonService, '_compare_xml')
    @patch('core.tree_comparison.PoBDecoder')
    def test_compare_pob_codes(self, mock_decoder, mock_compare_xml):
        """Test comparing two PoB codes."""
        mock_decoder.decode_pob_code.side_effect = ["<xml>your</xml>", "<xml>target</xml>"]
        mock_compare_xml.return_value = Mock()

        service = TreeComparisonService()
        service.compare_pob_codes("code1", "code2", "My Build", "Target Build")

        assert mock_decoder.decode_pob_code.call_count == 2
        mock_compare_xml.assert_called_once()

    def test_compare_profile_to_code_no_manager(self):
        """Test compare_profile_to_code raises without manager."""
        service = TreeComparisonService()

        with pytest.raises(ValueError, match="CharacterManager not available"):
            service.compare_profile_to_code("profile", "code")

    def test_compare_profile_to_code_profile_not_found(self):
        """Test compare_profile_to_code raises for missing profile."""
        mock_manager = Mock()
        mock_manager.get_profile.return_value = None

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="Profile not found"):
            service.compare_profile_to_code("missing_profile", "code")

    def test_compare_profile_to_code_no_pob_code(self):
        """Test compare_profile_to_code raises when profile has no PoB code."""
        mock_profile = Mock()
        mock_profile.pob_code = None
        mock_manager = Mock()
        mock_manager.get_profile.return_value = mock_profile

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="has no PoB code stored"):
            service.compare_profile_to_code("my_profile", "code")

    def test_compare_profiles_no_manager(self):
        """Test compare_profiles raises without manager."""
        service = TreeComparisonService()

        with pytest.raises(ValueError, match="CharacterManager not available"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_first_not_found(self):
        """Test compare_profiles raises for missing first profile."""
        mock_manager = Mock()
        mock_manager.get_profile.side_effect = [None, Mock()]

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="Profile not found: profile1"):
            service.compare_profiles("profile1", "profile2")

    def test_compare_profiles_second_not_found(self):
        """Test compare_profiles raises for missing second profile."""
        mock_profile = Mock()
        mock_profile.pob_code = "valid_code"
        mock_manager = Mock()
        mock_manager.get_profile.side_effect = [mock_profile, None]

        service = TreeComparisonService(character_manager=mock_manager)

        with pytest.raises(ValueError, match="Profile not found: profile2"):
            service.compare_profiles("profile1", "profile2")

    def test_format_comparison_report(self):
        """Test report formatting."""
        result = TreeComparisonResult(
            similarity_percent=85.0,
            shared_count=80,
            missing_count=10,
            extra_count=5,
            shared_nodes=[],
            missing_nodes=[],
            extra_nodes=[],
            missing_masteries=[],
            your_build_name="My Build",
            target_build_name="Guide",
            your_node_count=85,
            target_node_count=90,
        )

        service = TreeComparisonService()
        report = service.format_comparison_report(result)

        assert "My Build vs Guide" in report
        assert "85.0%" in report
        assert "85 nodes" in report
        assert "90 nodes" in report
        assert "Shared nodes: 80" in report
        assert "missing: 10" in report
        assert "Extra nodes you have: 5" in report

    def test_format_report_with_masteries(self):
        """Test report includes mastery info when present."""
        result = TreeComparisonResult(
            similarity_percent=75.0,
            shared_count=70,
            missing_count=15,
            extra_count=10,
            shared_nodes=[],
            missing_nodes=[],
            extra_nodes=[],
            missing_masteries=[(100, 1), (200, 2)],
            your_build_name="A",
            target_build_name="B",
            your_node_count=80,
            target_node_count=85,
        )

        service = TreeComparisonService()
        report = service.format_comparison_report(result)

        assert "masteries: 2" in report


class TestTreeComparisonXML:
    """Tests for XML comparison internals."""

    def test_compare_xml_empty_specs(self):
        """Test _compare_xml handles empty tree specs."""
        service = TreeComparisonService()

        # Mock parser to return empty list
        service.parser = Mock()
        service.parser.parse_tree_specs.return_value = []

        with pytest.raises(ValueError, match="Could not parse tree from your build"):
            service._compare_xml("<xml>a</xml>", "<xml>b</xml>", "A", "B")

    def test_compare_xml_target_empty_specs(self):
        """Test _compare_xml handles empty target specs."""
        service = TreeComparisonService()

        mock_spec = Mock()
        mock_spec.nodes = {1, 2, 3}
        mock_spec.mastery_effects = []

        service.parser = Mock()
        service.parser.parse_tree_specs.side_effect = [[mock_spec], []]

        with pytest.raises(ValueError, match="Could not parse tree from target build"):
            service._compare_xml("<xml>a</xml>", "<xml>b</xml>", "A", "B")

    def test_compare_xml_identical_trees(self):
        """Test comparing identical trees."""
        service = TreeComparisonService()

        mock_spec = Mock()
        mock_spec.nodes = {1, 2, 3, 4, 5}
        mock_spec.mastery_effects = []

        mock_delta = Mock()
        mock_delta.shared_nodes = [1, 2, 3, 4, 5]
        mock_delta.missing_nodes = []
        mock_delta.extra_nodes = []
        mock_delta.missing_masteries = []

        service.parser = Mock()
        service.parser.parse_tree_specs.return_value = [mock_spec]
        service.comparator = Mock()
        service.comparator.compare_trees.return_value = mock_delta

        result = service._compare_xml("<a/>", "<b/>", "A", "B")

        assert result.similarity_percent == 100.0
        assert result.missing_count == 0
        assert result.extra_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
