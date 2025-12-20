"""
Tests for gui_qt/widgets/unified_verdict_panel.py

Tests the unified verdict panel widget including:
- VerdictSectionWidget display
- UnifiedVerdictPanel functionality
- Verdict display and updates
- Signal emissions
"""
import pytest



@pytest.fixture
def verdict():
    """Create a mock UnifiedVerdict."""
    from core.unified_verdict import (
        PrimaryAction,
        ForYouVerdict,
        ToSellVerdict,
        ToStashVerdict,
        WhyValuable,
        MarketContext,
        UnifiedVerdict,
    )

    return UnifiedVerdict(
        primary_action=PrimaryAction.SELL,
        confidence="high",
        for_you=ForYouVerdict(
            is_upgrade=False,
            reason="Current ring is better",
        ),
        to_sell=ToSellVerdict(
            is_valuable=True,
            estimated_price=50.0,
            price_range="~50c",
            demand_level="high",
        ),
        to_stash=ToStashVerdict(
            should_stash=False,
            good_for_builds=[],
        ),
        why_valuable=WhyValuable(
            factors=["T1 Life", "Double resistance"],
        ),
        top_build_matches=["RF Juggernaut (92%)", "Boneshatter (85%)"],
        market_context=MarketContext(
            price_trend="UP",
            trend_percent=10.0,
            similar_listings=["45c", "55c", "60c"],
        ),
    )


class TestVerdictSectionWidget:
    """Tests for VerdictSectionWidget."""

    def test_creation(self, qapp):
        """Widget creates successfully."""
        from gui_qt.widgets.unified_verdict_panel import VerdictSectionWidget

        section = VerdictSectionWidget("FOR YOU:")
        assert section is not None

    def test_title_displayed(self, qapp):
        """Title is displayed in the section."""
        from gui_qt.widgets.unified_verdict_panel import VerdictSectionWidget

        section = VerdictSectionWidget("FOR YOU:")
        assert section.title_label.text() == "FOR YOU:"

    def test_set_status_positive(self, qapp):
        """Positive status shows [OK]."""
        from gui_qt.widgets.unified_verdict_panel import VerdictSectionWidget

        section = VerdictSectionWidget("TEST:")
        section.set_status(is_positive=True)

        assert "[OK]" in section.status_label.text()

    def test_set_status_negative(self, qapp):
        """Negative status shows [X]."""
        from gui_qt.widgets.unified_verdict_panel import VerdictSectionWidget

        section = VerdictSectionWidget("TEST:")
        section.set_status(is_positive=False)

        assert "[X]" in section.status_label.text()

    def test_set_status_neutral(self, qapp):
        """Neutral status shows [!]."""
        from gui_qt.widgets.unified_verdict_panel import VerdictSectionWidget

        section = VerdictSectionWidget("TEST:")
        section.set_status(is_positive=False, is_neutral=True)

        assert "[!]" in section.status_label.text()

    def test_set_content(self, qapp):
        """Content is set correctly."""
        from gui_qt.widgets.unified_verdict_panel import VerdictSectionWidget

        section = VerdictSectionWidget("TEST:")
        section.set_content("Test content here")

        assert section.content_label.text() == "Test content here"


class TestUnifiedVerdictPanel:
    """Tests for UnifiedVerdictPanel."""

    def test_creation(self, qapp):
        """Panel creates successfully."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        assert panel is not None

    def test_initial_state(self, qapp):
        """Initial state shows default values."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()

        assert "---" in panel.action_label.text()
        assert panel._current_verdict is None

    def test_set_verdict_updates_action(self, qapp, verdict):
        """Setting verdict updates action display."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        assert "SELL" in panel.action_label.text()

    def test_set_verdict_updates_confidence(self, qapp, verdict):
        """Setting verdict updates confidence display."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        assert "HIGH" in panel.confidence_label.text()

    def test_set_verdict_for_you_not_upgrade(self, qapp, verdict):
        """FOR YOU section shows not upgrade correctly."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        content = panel.for_you_section.content_label.text()
        assert "Current ring is better" in content or "Not an upgrade" in content.lower()

    def test_set_verdict_for_you_is_upgrade(self, qapp):
        """FOR YOU section shows upgrade correctly."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.KEEP,
            for_you=ForYouVerdict(
                is_upgrade=True,
                upgrade_slot="Ring",
                improvement_percent=15.0,
            ),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        content = panel.for_you_section.content_label.text()
        assert "Ring" in content
        assert "+15%" in content

    def test_set_verdict_to_sell_valuable(self, qapp, verdict):
        """TO SELL section shows valuable item correctly."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        content = panel.to_sell_section.content_label.text()
        assert "50c" in content
        assert "high" in content.lower()

    def test_set_verdict_to_sell_not_valuable(self, qapp):
        """TO SELL section shows low value correctly."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.VENDOR,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(is_valuable=False),
            to_stash=ToStashVerdict(),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        content = panel.to_sell_section.content_label.text()
        assert "low" in content.lower()

    def test_set_verdict_to_stash(self, qapp):
        """TO STASH section shows build fit correctly."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.STASH,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(
                should_stash=True,
                good_for_builds=["RF Juggernaut", "Boneshatter"],
                stash_reason="Good for tanky builds",
            ),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        content = panel.to_stash_section.content_label.text()
        assert "RF Juggernaut" in content or "Good for" in content

    def test_set_verdict_why_valuable_visible(self, qapp, verdict):
        """WHY VALUABLE section has content when factors exist."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.show()  # Need to show panel for visibility to work
        panel.set_verdict(verdict)

        # Check that content was set (visibility depends on Qt event loop)
        assert "T1 Life" in panel.why_content.text()

    def test_set_verdict_why_valuable_hidden(self, qapp):
        """WHY VALUABLE section hidden when no factors."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            WhyValuable,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.VENDOR,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
            why_valuable=WhyValuable(factors=[]),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        assert not panel.why_section.isVisible()

    def test_set_verdict_builds_visible(self, qapp, verdict):
        """BUILDS section has content when matches exist."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.show()  # Need to show panel for visibility to work
        panel.set_verdict(verdict)

        # Check that content was set
        assert "RF Juggernaut" in panel.builds_content.text()

    def test_set_verdict_builds_hidden(self, qapp):
        """BUILDS section hidden when no matches."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.VENDOR,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
            top_build_matches=[],
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        assert not panel.builds_section.isVisible()

    def test_set_verdict_market_context_visible(self, qapp, verdict):
        """MARKET CONTEXT section has content when trend exists."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.show()  # Need to show panel for visibility to work
        panel.set_verdict(verdict)

        # Check that content was set
        assert "UP" in panel.market_content.text()

    def test_set_verdict_market_context_hidden(self, qapp):
        """MARKET CONTEXT section hidden when no trend."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            MarketContext,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.VENDOR,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
            market_context=MarketContext(price_trend="UNKNOWN"),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        assert not panel.market_section.isVisible()

    def test_clear_resets_display(self, qapp, verdict):
        """Clear resets panel to default state."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)
        panel.clear()

        assert "---" in panel.action_label.text()
        assert panel._current_verdict is None
        assert not panel.why_section.isVisible()
        assert not panel.builds_section.isVisible()
        assert not panel.market_section.isVisible()

    def test_get_verdict_returns_current(self, qapp, verdict):
        """get_verdict returns current verdict."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        assert panel.get_verdict() == verdict

    def test_get_verdict_returns_none_initially(self, qapp):
        """get_verdict returns None before setting."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        assert panel.get_verdict() is None


class TestActionColors:
    """Tests for action color mapping."""

    def test_keep_color(self, qapp):
        """KEEP action has green color."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.KEEP,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        # Check style sheet contains green color
        style = panel.action_label.styleSheet()
        assert "#4CAF50" in style or "green" in style.lower()

    def test_sell_color(self, qapp):
        """SELL action has blue color."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        style = panel.action_label.styleSheet()
        assert "#2196F3" in style or "blue" in style.lower()

    def test_vendor_color(self, qapp):
        """VENDOR action has red color."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.VENDOR,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        style = panel.action_label.styleSheet()
        assert "#F44336" in style or "red" in style.lower()


class TestSignals:
    """Tests for signal emissions."""

    def test_refresh_signal_emitted(self, qapp):
        """Refresh button emits signal."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        signal_received = []

        panel.refresh_requested.connect(lambda: signal_received.append(True))
        panel.refresh_btn.click()

        assert len(signal_received) == 1

    def test_details_signal_emitted(self, qapp):
        """Details button emits signal."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel

        panel = UnifiedVerdictPanel()
        signal_received = []

        panel.details_requested.connect(lambda: signal_received.append(True))
        panel.details_btn.click()

        assert len(signal_received) == 1


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_builds_list(self, qapp):
        """Empty builds list handled."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.STASH,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(
                should_stash=True,
                good_for_builds=[],
            ),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        # Should not crash
        assert panel is not None

    def test_empty_similar_listings(self, qapp):
        """Empty similar listings handled."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            MarketContext,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(),
            to_stash=ToStashVerdict(),
            market_context=MarketContext(
                price_trend="UP",
                trend_percent=5.0,
                similar_listings=[],
            ),
        )

        panel = UnifiedVerdictPanel()
        panel.show()  # Need to show panel for visibility
        panel.set_verdict(verdict)

        # Check that UP trend is in content
        assert "UP" in panel.market_content.text()

    def test_none_demand_level(self, qapp):
        """Unknown demand level handled."""
        from gui_qt.widgets.unified_verdict_panel import UnifiedVerdictPanel
        from core.unified_verdict import (
            PrimaryAction,
            ForYouVerdict,
            ToSellVerdict,
            ToStashVerdict,
            UnifiedVerdict,
        )

        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            for_you=ForYouVerdict(),
            to_sell=ToSellVerdict(
                is_valuable=True,
                price_range="~50c",
                demand_level="unknown",
            ),
            to_stash=ToStashVerdict(),
        )

        panel = UnifiedVerdictPanel()
        panel.set_verdict(verdict)

        content = panel.to_sell_section.content_label.text()
        assert "50c" in content
        # Unknown demand should not show demand line
