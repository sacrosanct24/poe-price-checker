"""Tests for gui_qt/widgets/skeleton_loader.py - Skeleton loading placeholders."""

import pytest
from unittest.mock import patch

from PyQt6.QtWidgets import QWidget

from gui_qt.widgets.skeleton_loader import (
    SkeletonBase,
    SkeletonText,
    SkeletonRect,
    SkeletonCircle,
    SkeletonTableRow,
    SkeletonCard,
    SkeletonResultsTable,
    SkeletonItemInspector,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_skeleton_state():
    """Reset SkeletonBase class state between tests."""
    # Clear instances to prevent test interference
    SkeletonBase._instances.clear()
    SkeletonBase._shimmer_offset = 0.0
    if SkeletonBase._shimmer_timer is not None:
        SkeletonBase._shimmer_timer.stop()
        SkeletonBase._shimmer_timer = None
    yield
    # Cleanup after test
    SkeletonBase._instances.clear()
    if SkeletonBase._shimmer_timer is not None:
        SkeletonBase._shimmer_timer.stop()
        SkeletonBase._shimmer_timer = None


# =============================================================================
# SkeletonBase Tests
# =============================================================================


class TestSkeletonBaseInit:
    """Tests for SkeletonBase initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_default_values(self, mock_motion, qtbot):
        """Should initialize with default values."""
        skeleton = SkeletonBase()
        qtbot.addWidget(skeleton)

        assert skeleton._animate is True
        assert skeleton._base_color.name() == "#3a3a45"
        assert skeleton._highlight_color.name() == "#4a4a55"

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_colors(self, mock_motion, qtbot):
        """Should accept custom colors."""
        skeleton = SkeletonBase(color="#ff0000", highlight_color="#00ff00")
        qtbot.addWidget(skeleton)

        assert skeleton._base_color.name() == "#ff0000"
        assert skeleton._highlight_color.name() == "#00ff00"

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=True)
    def test_init_respects_reduced_motion(self, mock_motion, qtbot):
        """Should disable animation when reduce motion is enabled."""
        skeleton = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton)

        assert skeleton._animate is False

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_animate_false(self, mock_motion, qtbot):
        """Should respect animate=False."""
        skeleton = SkeletonBase(animate=False)
        qtbot.addWidget(skeleton)

        assert skeleton._animate is False

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_registers_for_shimmer(self, mock_motion, qtbot):
        """Should register instance for shimmer updates when animated."""
        skeleton = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton)

        assert skeleton in SkeletonBase._instances


class TestSkeletonBaseTimer:
    """Tests for shimmer timer."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_timer_starts_on_first_animated_instance(self, mock_motion, qtbot):
        """Should start timer when first animated instance created."""
        assert SkeletonBase._shimmer_timer is None

        skeleton = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton)

        assert SkeletonBase._shimmer_timer is not None
        assert SkeletonBase._shimmer_timer.isActive()

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_timer_shared_across_instances(self, mock_motion, qtbot):
        """Should share timer across multiple instances."""
        skeleton1 = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton1)

        timer1 = SkeletonBase._shimmer_timer

        skeleton2 = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton2)

        assert SkeletonBase._shimmer_timer is timer1


class TestSkeletonBaseShimmerUpdate:
    """Tests for shimmer animation."""

    def test_update_shimmer_increments_offset(self):
        """Should increment shimmer offset."""
        SkeletonBase._shimmer_offset = 0.0
        SkeletonBase._update_shimmer()

        assert SkeletonBase._shimmer_offset == pytest.approx(0.033, abs=0.001)

    def test_update_shimmer_wraps_at_one(self):
        """Should wrap offset back to 0 when exceeding 1."""
        SkeletonBase._shimmer_offset = 0.99
        SkeletonBase._update_shimmer()

        assert SkeletonBase._shimmer_offset == 0.0


class TestSkeletonBaseCrossFade:
    """Tests for cross-fade transition."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=True)
    def test_cross_fade_immediate_with_reduced_motion(self, mock_motion, qtbot):
        """Should instantly swap widgets when reduce motion enabled."""
        skeleton = SkeletonBase(animate=False)
        target = QWidget()
        qtbot.addWidget(skeleton)
        qtbot.addWidget(target)

        skeleton.show()
        target.hide()

        skeleton.cross_fade_to(target)

        assert skeleton.isHidden()
        assert not target.isHidden()

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_cross_fade_sets_up_animations(self, mock_motion, qtbot):
        """Should set up fade animations."""
        skeleton = SkeletonBase(animate=True)
        target = QWidget()
        qtbot.addWidget(skeleton)
        qtbot.addWidget(target)

        skeleton.show()
        skeleton.cross_fade_to(target)

        # Animations should be stored to prevent GC
        assert hasattr(skeleton, '_fade_out_anim')
        assert hasattr(skeleton, '_target_fade_anim')


class TestSkeletonBaseVisibility:
    """Tests for show/hide behavior."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_hide_event_removes_from_instances(self, mock_motion, qtbot):
        """Should remove from instances when hideEvent is called."""
        skeleton = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton)

        assert skeleton in SkeletonBase._instances

        # Manually call hideEvent to simulate being hidden
        from PyQt6.QtGui import QHideEvent
        skeleton.hideEvent(QHideEvent())

        assert skeleton not in SkeletonBase._instances

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_show_event_re_registers_instance(self, mock_motion, qtbot):
        """Should re-register when showEvent is called after hiding."""
        skeleton = SkeletonBase(animate=True)
        qtbot.addWidget(skeleton)

        # Remove from instances manually
        from PyQt6.QtGui import QHideEvent
        skeleton.hideEvent(QHideEvent())
        assert skeleton not in SkeletonBase._instances

        # Re-register via showEvent
        from PyQt6.QtGui import QShowEvent
        skeleton.showEvent(QShowEvent())
        assert skeleton in SkeletonBase._instances


# =============================================================================
# SkeletonText Tests
# =============================================================================


class TestSkeletonTextInit:
    """Tests for SkeletonText initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_default_height(self, mock_motion, qtbot):
        """Should use default height."""
        skeleton = SkeletonText()
        qtbot.addWidget(skeleton)

        assert skeleton.height() == 16

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_height(self, mock_motion, qtbot):
        """Should accept custom height."""
        skeleton = SkeletonText(height=24)
        qtbot.addWidget(skeleton)

        assert skeleton.height() == 24

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_fixed_width(self, mock_motion, qtbot):
        """Should accept fixed width."""
        skeleton = SkeletonText(width=100, height=20)
        qtbot.addWidget(skeleton)

        assert skeleton.width() == 100
        assert skeleton.height() == 20

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_width_percent(self, mock_motion, qtbot):
        """Should store width percent."""
        skeleton = SkeletonText(width_percent=0.5)
        qtbot.addWidget(skeleton)

        assert skeleton._width_percent == 0.5


# =============================================================================
# SkeletonRect Tests
# =============================================================================


class TestSkeletonRectInit:
    """Tests for SkeletonRect initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_fixed_size(self, mock_motion, qtbot):
        """Should accept fixed dimensions."""
        skeleton = SkeletonRect(width=100, height=50)
        qtbot.addWidget(skeleton)

        assert skeleton.width() == 100
        assert skeleton.height() == 50

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_radius(self, mock_motion, qtbot):
        """Should accept custom border radius."""
        skeleton = SkeletonRect(radius=10)
        qtbot.addWidget(skeleton)

        assert skeleton._radius == 10

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_width_only(self, mock_motion, qtbot):
        """Should accept width only."""
        skeleton = SkeletonRect(width=200)
        qtbot.addWidget(skeleton)

        assert skeleton.width() == 200

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_height_only(self, mock_motion, qtbot):
        """Should accept height only."""
        skeleton = SkeletonRect(height=100)
        qtbot.addWidget(skeleton)

        assert skeleton.height() == 100


# =============================================================================
# SkeletonCircle Tests
# =============================================================================


class TestSkeletonCircleInit:
    """Tests for SkeletonCircle initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_default_diameter(self, mock_motion, qtbot):
        """Should use default diameter."""
        skeleton = SkeletonCircle()
        qtbot.addWidget(skeleton)

        assert skeleton.width() == 40
        assert skeleton.height() == 40

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_diameter(self, mock_motion, qtbot):
        """Should accept custom diameter."""
        skeleton = SkeletonCircle(diameter=60)
        qtbot.addWidget(skeleton)

        assert skeleton.width() == 60
        assert skeleton.height() == 60


# =============================================================================
# SkeletonTableRow Tests
# =============================================================================


class TestSkeletonTableRowInit:
    """Tests for SkeletonTableRow initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_default_columns(self, mock_motion, qtbot):
        """Should create default 4 columns."""
        skeleton = SkeletonTableRow()
        qtbot.addWidget(skeleton)

        # Layout should have 4 skeleton text widgets
        layout = skeleton.layout()
        assert layout.count() == 4

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_columns(self, mock_motion, qtbot):
        """Should create specified number of columns."""
        skeleton = SkeletonTableRow(columns=6)
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        assert layout.count() == 6

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_height(self, mock_motion, qtbot):
        """Should set custom row height."""
        skeleton = SkeletonTableRow(height=48)
        qtbot.addWidget(skeleton)

        assert skeleton.height() == 48

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_column_widths(self, mock_motion, qtbot):
        """Should accept custom column widths."""
        widths = [0.3, 0.4, 0.3]
        skeleton = SkeletonTableRow(columns=3, column_widths=widths)
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        assert layout.count() == 3


# =============================================================================
# SkeletonCard Tests
# =============================================================================


class TestSkeletonCardInit:
    """Tests for SkeletonCard initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_default_elements(self, mock_motion, qtbot):
        """Should create title, subtitle, and content by default."""
        skeleton = SkeletonCard()
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # title + subtitle + 3 content lines + stretch = 6 items
        assert layout.count() >= 5

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_with_image(self, mock_motion, qtbot):
        """Should include image placeholder when requested."""
        skeleton = SkeletonCard(show_image=True)
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # image + title + subtitle + 3 lines + stretch = 7 items
        assert layout.count() >= 6

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_without_title(self, mock_motion, qtbot):
        """Should exclude title when disabled."""
        skeleton = SkeletonCard(show_title=False)
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # subtitle + 3 lines + stretch = 5 items
        assert layout.count() >= 4

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_content_lines(self, mock_motion, qtbot):
        """Should create specified number of content lines."""
        skeleton = SkeletonCard(content_lines=5)
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # title + subtitle + 5 lines + stretch = 8 items
        assert layout.count() >= 7


# =============================================================================
# SkeletonResultsTable Tests
# =============================================================================


class TestSkeletonResultsTableInit:
    """Tests for SkeletonResultsTable initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_default_rows(self, mock_motion, qtbot):
        """Should create default 5 data rows plus header."""
        skeleton = SkeletonResultsTable()
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # header + 5 rows + stretch = 7 items
        assert layout.count() == 7

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_rows(self, mock_motion, qtbot):
        """Should create specified number of rows."""
        skeleton = SkeletonResultsTable(rows=10)
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # header + 10 rows + stretch = 12 items
        assert layout.count() == 12

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_custom_columns(self, mock_motion, qtbot):
        """Should pass columns to row skeletons."""
        skeleton = SkeletonResultsTable(columns=8)
        qtbot.addWidget(skeleton)

        # Get first data row (index 1, after header)
        layout = skeleton.layout()
        first_row = layout.itemAt(1).widget()
        row_layout = first_row.layout()

        assert row_layout.count() == 8


# =============================================================================
# SkeletonItemInspector Tests
# =============================================================================


class TestSkeletonItemInspectorInit:
    """Tests for SkeletonItemInspector initialization."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_creates_elements(self, mock_motion, qtbot):
        """Should create name, base, separator, and mod lines."""
        skeleton = SkeletonItemInspector()
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        # name + base + spacing + sep + spacing + 6 mods + stretch = many items
        assert layout.count() >= 10

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_init_layout_margins(self, mock_motion, qtbot):
        """Should set layout margins."""
        skeleton = SkeletonItemInspector()
        qtbot.addWidget(skeleton)

        layout = skeleton.layout()
        margins = layout.contentsMargins()
        assert margins.left() > 0
        assert margins.top() > 0


# =============================================================================
# Paint Tests
# =============================================================================


class TestSkeletonPaint:
    """Tests for paint methods."""

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_paint_event_does_not_crash(self, mock_motion, qtbot):
        """Should paint without errors."""
        skeleton = SkeletonBase()
        qtbot.addWidget(skeleton)
        skeleton.show()

        # Force repaint
        skeleton.repaint()

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_text_paint_does_not_crash(self, mock_motion, qtbot):
        """Should paint text skeleton without errors."""
        skeleton = SkeletonText(width_percent=0.5)
        qtbot.addWidget(skeleton)
        skeleton.show()
        skeleton.repaint()

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_circle_paint_does_not_crash(self, mock_motion, qtbot):
        """Should paint circle skeleton without errors."""
        skeleton = SkeletonCircle()
        qtbot.addWidget(skeleton)
        skeleton.show()
        skeleton.repaint()

    @patch('gui_qt.widgets.skeleton_loader.should_reduce_motion', return_value=False)
    def test_rect_paint_does_not_crash(self, mock_motion, qtbot):
        """Should paint rect skeleton without errors."""
        skeleton = SkeletonRect()
        qtbot.addWidget(skeleton)
        skeleton.show()
        skeleton.repaint()
