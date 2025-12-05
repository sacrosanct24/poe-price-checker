"""
Onboarding Package - First-run experience and feature discovery.

This package provides components for user onboarding:
- Welcome wizard for first-run experience
- Feature spotlights for highlighting new/useful features
- Contextual tips and hints

Usage:
    from gui_qt.onboarding import (
        WelcomeWizard,
        FeatureSpotlight,
        show_feature_tip,
    )

    # Show welcome wizard on first run
    if not config.onboarding_completed:
        wizard = WelcomeWizard(main_window)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            config.onboarding_completed = True

    # Highlight a feature
    spotlight = FeatureSpotlight(
        target=price_check_button,
        title="Quick Price Check",
        description="Press Ctrl+V to instantly check prices",
    )
    spotlight.show()
"""

from gui_qt.onboarding.welcome_wizard import (
    WelcomeWizard,
    WizardPage,
)
from gui_qt.onboarding.feature_spotlight import (
    FeatureSpotlight,
    SpotlightManager,
    show_feature_tip,
    TipPosition,
)

__all__ = [
    "WelcomeWizard",
    "WizardPage",
    "FeatureSpotlight",
    "SpotlightManager",
    "show_feature_tip",
    "TipPosition",
]
