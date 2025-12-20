"""
Welcome Wizard - First-run onboarding experience.

Multi-step wizard that introduces new users to the application,
helping them configure settings and learn key features.

Usage:
    from gui_qt.onboarding.welcome_wizard import WelcomeWizard

    wizard = WelcomeWizard(parent)
    if wizard.exec() == QDialog.DialogCode.Accepted:
        # User completed onboarding
        settings = wizard.get_settings()
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QStackedWidget,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
)

from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    Duration,
    should_reduce_motion,
)


class WizardPage(QWidget):
    """
    Base class for wizard pages.

    Subclass this to create custom wizard pages.
    """

    # Emitted when page content changes (for validation)
    content_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = ""
        self._subtitle = ""

    @property
    def title(self) -> str:
        """Page title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def subtitle(self) -> str:
        """Page subtitle."""
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value: str) -> None:
        self._subtitle = value

    def validate(self) -> bool:
        """
        Validate page before proceeding.

        Override in subclasses to add validation.

        Returns:
            True if page is valid and user can proceed
        """
        return True

    def on_enter(self) -> None:
        """Called when page becomes visible."""
        pass

    def on_leave(self) -> None:
        """Called when leaving page."""
        pass

    def get_data(self) -> dict:
        """
        Get data collected on this page.

        Override in subclasses to return collected data.

        Returns:
            Dictionary of collected data
        """
        return {}


class WelcomePage(WizardPage):
    """Welcome/intro page."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = "Welcome to PoE Price Checker"
        self.subtitle = "Your companion for Path of Exile economy"

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Spacing.LG)

        # Icon/logo placeholder
        icon_label = QLabel()
        icon_label.setFixedSize(120, 120)
        icon_label.setStyleSheet("""
            background-color: #8b5cf6;
            border-radius: 24px;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Welcome text
        welcome_text = QLabel("""
            <p style="font-size: 16px; color: #e4e4e7; text-align: center;">
            Get instant price checks, track your economy,<br>
            and optimize your builds with AI assistance.
            </p>
        """)
        welcome_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_text)

        # Features list
        features = [
            "Instant price checking (Ctrl+V)",
            "Multi-source pricing (poe.ninja, Trade API)",
            "Rare item evaluation with mod analysis",
            "Path of Building integration",
            "AI-powered item insights",
        ]

        features_widget = QWidget()
        features_layout = QVBoxLayout(features_widget)
        features_layout.setSpacing(Spacing.SM)

        for feature in features:
            row = QHBoxLayout()
            row.setSpacing(Spacing.SM)

            check = QLabel("✓")
            check.setStyleSheet("color: #22c55e; font-weight: bold;")
            row.addWidget(check)

            text = QLabel(feature)
            text.setStyleSheet("color: #a1a1aa; font-size: 14px;")
            row.addWidget(text)
            row.addStretch()

            features_layout.addLayout(row)

        layout.addWidget(features_widget, alignment=Qt.AlignmentFlag.AlignCenter)


class ThemePage(WizardPage):
    """Theme selection page."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = "Choose Your Theme"
        self.subtitle = "Select a visual style that suits you"

        self._selected_theme = "dark"

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.LG)

        # Theme options
        self._button_group = QButtonGroup(self)

        themes = [
            ("dark", "Dark", "Easy on the eyes for long sessions", "#1e1e2e"),
            ("light", "Light", "Bright and clean appearance", "#f4f4f5"),
            ("system", "System", "Match your OS preference", "#3a3a45"),
        ]

        for theme_id, name, desc, color in themes:
            option = self._create_theme_option(theme_id, name, desc, color)
            layout.addWidget(option)

        layout.addStretch()

    def _create_theme_option(
        self, theme_id: str, name: str, description: str, color: str
    ) -> QWidget:
        """Create a theme option widget."""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #2a2a35;
                border: 2px solid transparent;
                border-radius: {BorderRadius.MD}px;
                padding: {Spacing.MD}px;
            }}
            QFrame:hover {{
                border-color: #4a4a55;
            }}
        """)
        container.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(container)
        layout.setSpacing(Spacing.MD)

        # Color preview
        preview = QLabel()
        preview.setFixedSize(48, 48)
        preview.setStyleSheet(f"""
            background-color: {color};
            border-radius: {BorderRadius.SM}px;
            border: 1px solid #4a4a55;
        """)
        layout.addWidget(preview)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(Spacing.XS)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #e4e4e7;")
        text_layout.addWidget(name_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 13px; color: #a1a1aa;")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Radio button
        radio = QRadioButton()
        radio.setChecked(theme_id == "dark")
        radio.toggled.connect(lambda checked: self._on_theme_selected(theme_id) if checked else None)
        self._button_group.addButton(radio)
        layout.addWidget(radio)

        return container

    def _on_theme_selected(self, theme_id: str) -> None:
        """Handle theme selection."""
        self._selected_theme = theme_id
        self.content_changed.emit()

    def get_data(self) -> dict:
        return {"theme": self._selected_theme}


class QuickDemoPage(WizardPage):
    """Interactive demo page showing how to use the app."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = "How It Works"
        self.subtitle = "Price checking in 3 simple steps"

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.XL)

        steps = [
            ("1", "Copy Item", "In-game, hover over an item and press Ctrl+C"),
            ("2", "Check Price", "Switch to Price Checker - it auto-detects the item"),
            ("3", "See Results", "View prices from multiple sources instantly"),
        ]

        for number, title, desc in steps:
            step_widget = self._create_step(number, title, desc)
            layout.addWidget(step_widget)

        layout.addStretch()

        # Tip
        tip = QLabel(
            "💡 Tip: Keep the app running in the background. "
            "Press Ctrl+V anytime to check prices!"
        )
        tip.setStyleSheet("""
            background-color: #3a3a45;
            border-radius: 8px;
            padding: 12px;
            color: #a1a1aa;
            font-size: 13px;
        """)
        tip.setWordWrap(True)
        layout.addWidget(tip)

    def _create_step(self, number: str, title: str, description: str) -> QWidget:
        """Create a step widget."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(Spacing.MD)

        # Number circle
        num_label = QLabel(number)
        num_label.setFixedSize(40, 40)
        num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_label.setStyleSheet("""
            background-color: #8b5cf6;
            color: white;
            border-radius: 20px;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(num_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(Spacing.XS)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #e4e4e7;")
        text_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 13px; color: #a1a1aa;")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        return container


class SetupPage(WizardPage):
    """Optional setup page for additional configuration."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = "Quick Setup"
        self.subtitle = "Configure optional features (you can change these later)"

        self._settings = {
            "minimize_to_tray": False,
            "start_minimized": False,
            "enable_ai": False,
        }

        layout = QVBoxLayout(self)
        layout.setSpacing(Spacing.MD)

        options = [
            ("minimize_to_tray", "Minimize button hides to tray", "Use File > Minimize to Tray for explicit control", False),
            ("start_minimized", "Start minimized", "Launch to tray when opening the app", False),
            ("enable_ai", "Enable AI insights", "Get AI-powered analysis of your items (requires API key)", False),
        ]

        for key, title, desc, default in options:
            checkbox = self._create_option(key, title, desc, default)
            layout.addWidget(checkbox)

        layout.addStretch()

    def _create_option(
        self, key: str, title: str, description: str, default: bool
    ) -> QWidget:
        """Create an option checkbox."""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #2a2a35;
                border-radius: {BorderRadius.MD}px;
                padding: {Spacing.MD}px;
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setSpacing(Spacing.MD)

        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(default)
        checkbox.toggled.connect(lambda checked: self._on_option_changed(key, checked))
        layout.addWidget(checkbox)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(Spacing.XS)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #e4e4e7;")
        text_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        return container

    def _on_option_changed(self, key: str, checked: bool) -> None:
        """Handle option change."""
        self._settings[key] = checked
        self.content_changed.emit()

    def get_data(self) -> dict:
        return self._settings


class CompletePage(WizardPage):
    """Completion page."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = "You're All Set!"
        self.subtitle = "Start checking prices now"

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Spacing.LG)

        # Success icon
        icon_label = QLabel("🎉")
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Message
        message = QLabel("""
            <p style="font-size: 16px; color: #e4e4e7; text-align: center;">
            You're ready to start price checking!<br><br>
            Copy any item in-game and switch to this window<br>
            to see instant price information.
            </p>
        """)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)

        # Keyboard shortcut reminder
        shortcut = QLabel("Press Ctrl+V anytime to check prices")
        shortcut.setStyleSheet("""
            background-color: #8b5cf6;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
        """)
        shortcut.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(shortcut, alignment=Qt.AlignmentFlag.AlignCenter)


class WelcomeWizard(QDialog):
    """
    Welcome wizard dialog for first-run onboarding.

    Guides users through initial setup with multiple pages.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_page = 0
        self._collected_data: dict = {}

        self.setWindowTitle("Welcome")
        self.setFixedSize(600, 500)
        self.setModal(True)

        self._apply_style()
        self._setup_ui()
        self._setup_pages()

    def _apply_style(self) -> None:
        """Apply dialog styling."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e2e;
            }}

            QPushButton {{
                background-color: #3a3a45;
                color: #e4e4e7;
                border: none;
                border-radius: {BorderRadius.SM}px;
                padding: 10px 20px;
                font-weight: 500;
                min-width: 100px;
            }}

            QPushButton:hover {{
                background-color: #4a4a55;
            }}

            QPushButton[primary="true"] {{
                background-color: #8b5cf6;
                color: white;
            }}

            QPushButton[primary="true"]:hover {{
                background-color: #9d6fff;
            }}

            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid #4a4a55;
                background-color: #2a2a35;
            }}

            QRadioButton::indicator:checked {{
                background-color: #8b5cf6;
                border-color: #8b5cf6;
            }}

            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #4a4a55;
                background-color: #2a2a35;
            }}

            QCheckBox::indicator:checked {{
                background-color: #8b5cf6;
                border-color: #8b5cf6;
            }}
        """)

    def _setup_ui(self) -> None:
        """Set up the UI structure."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with title
        header = QWidget()
        header.setStyleSheet("background-color: #2a2a35;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)

        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 22px; font-weight: 600; color: #e4e4e7;")
        header_layout.addWidget(self._title_label)

        self._subtitle_label = QLabel()
        self._subtitle_label.setStyleSheet("font-size: 14px; color: #a1a1aa;")
        header_layout.addWidget(self._subtitle_label)

        layout.addWidget(header)

        # Page content
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # Footer with navigation
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.LG)

        # Page indicator
        self._page_indicator = QLabel()
        self._page_indicator.setStyleSheet("color: #71717a; font-size: 13px;")
        footer_layout.addWidget(self._page_indicator)

        footer_layout.addStretch()

        # Navigation buttons
        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self._go_back)
        footer_layout.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setProperty("primary", True)
        self._next_btn.clicked.connect(self._go_next)
        footer_layout.addWidget(self._next_btn)

        layout.addWidget(footer)

    def _setup_pages(self) -> None:
        """Set up wizard pages."""
        self._pages = [
            WelcomePage(self),
            ThemePage(self),
            QuickDemoPage(self),
            SetupPage(self),
            CompletePage(self),
        ]

        for page in self._pages:
            self._stack.addWidget(page)

        self._update_ui()

    def _update_ui(self) -> None:
        """Update UI for current page."""
        page = self._pages[self._current_page]

        # Update header
        self._title_label.setText(page.title)
        self._subtitle_label.setText(page.subtitle)

        # Update page indicator
        self._page_indicator.setText(f"Step {self._current_page + 1} of {len(self._pages)}")

        # Update buttons
        self._back_btn.setVisible(self._current_page > 0)
        is_last = self._current_page == len(self._pages) - 1
        self._next_btn.setText("Get Started" if is_last else "Next")

        # Animate transition
        self._animate_page_change()

    def _animate_page_change(self) -> None:
        """Animate page transition."""
        if should_reduce_motion():
            self._stack.setCurrentIndex(self._current_page)
            return

        # Fade out/in effect
        effect = QGraphicsOpacityEffect(self._stack)
        self._stack.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(Duration.FAST)
        anim.setStartValue(0.5)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._stack.setCurrentIndex(self._current_page)
        anim.start()

        # Store reference
        self._page_animation = anim

    def _go_back(self) -> None:
        """Go to previous page."""
        if self._current_page > 0:
            self._pages[self._current_page].on_leave()
            self._current_page -= 1
            self._pages[self._current_page].on_enter()
            self._update_ui()

    def _go_next(self) -> None:
        """Go to next page or complete wizard."""
        page = self._pages[self._current_page]

        if not page.validate():
            return

        # Collect data from current page
        self._collected_data.update(page.get_data())
        page.on_leave()

        if self._current_page < len(self._pages) - 1:
            self._current_page += 1
            self._pages[self._current_page].on_enter()
            self._update_ui()
        else:
            # Complete wizard
            self.accept()

    def get_settings(self) -> dict:
        """
        Get all collected settings from the wizard.

        Returns:
            Dictionary of all settings collected across pages
        """
        return self._collected_data.copy()

    def sizeHint(self) -> QSize:
        return QSize(600, 500)
