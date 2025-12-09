"""
Base Dialog - Standardized dialog with consistent UX patterns.

Provides a foundation for all dialogs in the application with:
- Consistent button layout (Cancel | Primary)
- Keyboard shortcuts (Escape, Enter, Alt+letter)
- Geometry persistence across sessions
- Accessibility support
- Focus management

Usage:
    from gui_qt.dialogs.base_dialog import BaseDialog

    class MyDialog(BaseDialog):
        def __init__(self, parent=None):
            super().__init__(
                parent,
                title="My Dialog",
                modal=True,
                remember_geometry=True,
            )

            # Add content
            self.add_content(my_widget)

            # Add buttons
            self.add_button_row(
                primary_text="Save",
                secondary_text="Cancel",
                primary_action=self.save,
            )
"""

from typing import Optional, Callable

from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QFrame,
    QSizePolicy,
)

from gui_qt.design_system import Spacing, BorderRadius, Duration
from gui_qt.accessibility import (
    set_accessible_name,
    set_accessible_description,
    set_focus_order,
    install_dialog_shortcuts,
    add_button_mnemonic,
)


class BaseDialog(QDialog):
    """
    Standardized dialog base class.

    Features:
    - Consistent styling following design system
    - Keyboard shortcuts (Escape to close, Enter for primary action)
    - Tab order management
    - Geometry persistence
    - Accessibility labels
    """

    # Settings key prefix for geometry persistence
    SETTINGS_GROUP = "DialogGeometry"

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str = "",
        modal: bool = True,
        remember_geometry: bool = True,
        min_width: int = 400,
        min_height: int = 200,
        show_help: bool = False,
        help_text: str = "",
    ):
        """
        Initialize base dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            modal: Whether dialog blocks parent
            remember_geometry: Whether to save/restore position and size
            min_width: Minimum dialog width
            min_height: Minimum dialog height
            show_help: Whether to show help text below title
            help_text: Help text to display
        """
        super().__init__(parent)

        self._title = title
        self._remember_geometry = remember_geometry
        self._focusable_widgets: list[QWidget] = []
        self._primary_button: Optional[QPushButton] = None
        self._secondary_button: Optional[QPushButton] = None

        # Configure dialog
        self.setWindowTitle(title)
        self.setModal(modal)
        self.setMinimumSize(min_width, min_height)

        # Apply consistent styling
        self._apply_style()

        # Set up main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(
            Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG
        )
        self._main_layout.setSpacing(Spacing.MD)

        # Title section
        if title:
            self._add_title_section(title, help_text if show_help else "")

        # Content area (to be filled by subclasses)
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(Spacing.SM)
        self._main_layout.addWidget(self._content_area)

        # Button row (will be added by add_button_row)
        self._button_row: Optional[QWidget] = None

        # Install keyboard shortcuts
        self._setup_shortcuts()

        # Accessibility
        set_accessible_name(self, title)
        if help_text:
            set_accessible_description(self, help_text)

        # Restore geometry if enabled
        if remember_geometry:
            self._restore_geometry()

    def _apply_style(self) -> None:
        """Apply consistent dialog styling."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1e1e2e;
                border-radius: {BorderRadius.LG}px;
            }}

            QLabel {{
                color: #e4e4e7;
            }}

            QPushButton {{
                background-color: #3a3a45;
                color: #e4e4e7;
                border: none;
                border-radius: {BorderRadius.SM}px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }}

            QPushButton:hover {{
                background-color: #4a4a55;
            }}

            QPushButton:pressed {{
                background-color: #2a2a35;
            }}

            QPushButton:focus {{
                border: 2px solid #8b5cf6;
            }}

            QPushButton[primary="true"] {{
                background-color: #8b5cf6;
                color: white;
            }}

            QPushButton[primary="true"]:hover {{
                background-color: #9d6fff;
            }}

            QPushButton[primary="true"]:pressed {{
                background-color: #7c4ddb;
            }}

            QPushButton[destructive="true"] {{
                background-color: #ef4444;
                color: white;
            }}

            QPushButton[destructive="true"]:hover {{
                background-color: #f87171;
            }}

            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: #2a2a35;
                color: #e4e4e7;
                border: 1px solid #3a3a45;
                border-radius: {BorderRadius.SM}px;
                padding: 8px;
            }}

            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid #8b5cf6;
            }}

            QComboBox {{
                background-color: #2a2a35;
                color: #e4e4e7;
                border: 1px solid #3a3a45;
                border-radius: {BorderRadius.SM}px;
                padding: 8px;
            }}

            QComboBox:focus {{
                border: 2px solid #8b5cf6;
            }}

            QCheckBox {{
                color: #e4e4e7;
                spacing: 8px;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {BorderRadius.XS}px;
                border: 2px solid #3a3a45;
                background-color: #2a2a35;
            }}

            QCheckBox::indicator:checked {{
                background-color: #8b5cf6;
                border-color: #8b5cf6;
            }}

            QCheckBox::indicator:focus {{
                border-color: #8b5cf6;
            }}
        """)

    def _add_title_section(self, title: str, help_text: str) -> None:
        """Add title and optional help text."""
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #e4e4e7;
            padding-bottom: 4px;
        """)
        self._main_layout.addWidget(title_label)

        if help_text:
            help_label = QLabel(help_text)
            help_label.setStyleSheet("""
                font-size: 13px;
                color: #a1a1aa;
            """)
            help_label.setWordWrap(True)
            self._main_layout.addWidget(help_label)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #3a3a45; max-height: 1px;")
        self._main_layout.addWidget(separator)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Escape to close
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self.reject)

        # Enter to accept (handled specially)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        enter_shortcut.activated.connect(self._on_enter_pressed)

    def _on_enter_pressed(self) -> None:
        """Handle Enter key press."""
        # If a button has focus, click it
        focused = self.focusWidget()
        if isinstance(focused, QPushButton):
            focused.click()
        elif self._primary_button:
            self._primary_button.click()

    def add_content(self, widget: QWidget) -> None:
        """
        Add a widget to the content area.

        Args:
            widget: Widget to add
        """
        self._content_layout.addWidget(widget)

    def add_content_layout(self, layout) -> None:
        """
        Add a layout to the content area.

        Args:
            layout: Layout to add
        """
        self._content_layout.addLayout(layout)

    def add_stretch(self) -> None:
        """Add stretch to push content to top."""
        self._content_layout.addStretch()

    def add_button_row(
        self,
        primary_text: str = "Save",
        secondary_text: str = "Cancel",
        primary_action: Optional[Callable[[], None]] = None,
        secondary_action: Optional[Callable[[], None]] = None,
        destructive: bool = False,
        show_help_button: bool = False,
        help_action: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Add standardized button row.

        Buttons are ordered: [Help] | [stretch] | Cancel | Primary
        This follows platform conventions (primary action on right).

        Args:
            primary_text: Text for primary button
            secondary_text: Text for secondary button
            primary_action: Callback for primary button (default: accept)
            secondary_action: Callback for secondary button (default: reject)
            destructive: Style primary button as destructive (red)
            show_help_button: Show help button on left
            help_action: Callback for help button
        """
        if self._button_row:
            # Remove existing button row
            self._main_layout.removeWidget(self._button_row)
            self._button_row.deleteLater()

        self._button_row = QWidget()
        layout = QHBoxLayout(self._button_row)
        layout.setContentsMargins(0, Spacing.MD, 0, 0)
        layout.setSpacing(Spacing.SM)

        # Help button (optional, on left)
        if show_help_button:
            help_btn = QPushButton("Help")
            help_btn.clicked.connect(help_action or (lambda: None))
            add_button_mnemonic(help_btn, "H")
            layout.addWidget(help_btn)
            self._focusable_widgets.append(help_btn)

        layout.addStretch()

        # Secondary button (Cancel)
        self._secondary_button = QPushButton(secondary_text)
        self._secondary_button.clicked.connect(
            secondary_action or self.reject
        )
        # Add mnemonic if first char is unique
        if secondary_text:
            add_button_mnemonic(self._secondary_button, secondary_text[0])
        layout.addWidget(self._secondary_button)
        self._focusable_widgets.append(self._secondary_button)

        # Primary button
        self._primary_button = QPushButton(primary_text)
        self._primary_button.setProperty("primary", True)
        if destructive:
            self._primary_button.setProperty("destructive", True)
            self._primary_button.setProperty("primary", False)
        self._primary_button.setDefault(True)
        self._primary_button.clicked.connect(
            primary_action or self.accept
        )
        # Add mnemonic
        if primary_text:
            add_button_mnemonic(self._primary_button, primary_text[0])
        layout.addWidget(self._primary_button)
        self._focusable_widgets.append(self._primary_button)

        # Update styling
        style = self._primary_button.style()
        if style:
            style.unpolish(self._primary_button)
            style.polish(self._primary_button)

        self._main_layout.addWidget(self._button_row)

    def set_tab_order(self, widgets: list[QWidget]) -> None:
        """
        Set explicit tab order for widgets.

        Args:
            widgets: Widgets in desired tab order
        """
        all_widgets = widgets + self._focusable_widgets
        set_focus_order(all_widgets)

    def register_focusable(self, widget: QWidget) -> None:
        """
        Register a widget for tab order.

        Args:
            widget: Focusable widget to add
        """
        self._focusable_widgets.append(widget)

    def _restore_geometry(self) -> None:
        """Restore saved geometry."""
        settings = QSettings()
        settings.beginGroup(self.SETTINGS_GROUP)

        geometry = settings.value(self._geometry_key())
        if geometry:
            self.restoreGeometry(geometry)

        settings.endGroup()

    def _save_geometry(self) -> None:
        """Save current geometry."""
        if not self._remember_geometry:
            return

        settings = QSettings()
        settings.beginGroup(self.SETTINGS_GROUP)
        settings.setValue(self._geometry_key(), self.saveGeometry())
        settings.endGroup()

    def _geometry_key(self) -> str:
        """Get unique key for this dialog's geometry."""
        return self.__class__.__name__

    def closeEvent(self, event) -> None:
        """Save geometry on close."""
        self._save_geometry()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        """Save geometry when dialog finishes."""
        self._save_geometry()
        super().done(result)

    def showEvent(self, event) -> None:
        """Set initial focus when shown."""
        super().showEvent(event)

        # Focus first focusable widget
        if self._focusable_widgets:
            self._focusable_widgets[0].setFocus()

    def sizeHint(self) -> QSize:
        """Provide reasonable default size."""
        return QSize(450, 300)


class ConfirmDialog(BaseDialog):
    """
    Simple confirmation dialog.

    Usage:
        dialog = ConfirmDialog(
            parent,
            title="Confirm Delete",
            message="Are you sure you want to delete this item?",
            confirm_text="Delete",
            destructive=True,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # User confirmed
            ...
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str = "Confirm",
        message: str = "",
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        destructive: bool = False,
    ):
        """
        Initialize confirm dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            message: Confirmation message
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
            destructive: Style as destructive action
        """
        super().__init__(
            parent,
            title=title,
            modal=True,
            remember_geometry=False,
            min_width=350,
            min_height=150,
        )

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 14px; color: #e4e4e7;")
        self.add_content(msg_label)
        self.add_stretch()

        # Buttons
        self.add_button_row(
            primary_text=confirm_text,
            secondary_text=cancel_text,
            destructive=destructive,
        )


class InputDialog(BaseDialog):
    """
    Simple input dialog for getting a single value.

    Usage:
        dialog = InputDialog(
            parent,
            title="Enter Name",
            label="Name:",
            placeholder="Enter a name...",
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.value()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        title: str = "Input",
        label: str = "",
        placeholder: str = "",
        default_value: str = "",
        submit_text: str = "OK",
    ):
        """
        Initialize input dialog.

        Args:
            parent: Parent widget
            title: Dialog title
            label: Label for input field
            placeholder: Placeholder text
            default_value: Initial value
            submit_text: Text for submit button
        """
        super().__init__(
            parent,
            title=title,
            modal=True,
            remember_geometry=False,
            min_width=400,
            min_height=150,
        )

        from PyQt6.QtWidgets import QLineEdit

        # Label
        if label:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 14px; color: #e4e4e7;")
            self.add_content(lbl)

        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setText(default_value)
        self.add_content(self._input)
        self.register_focusable(self._input)

        self.add_stretch()

        # Buttons
        self.add_button_row(
            primary_text=submit_text,
            secondary_text="Cancel",
        )

        # Focus input
        self._input.setFocus()

    def value(self) -> str:
        """Get the input value."""
        return self._input.text()


def confirm(
    parent: Optional[QWidget],
    title: str,
    message: str,
    *,
    confirm_text: str = "Confirm",
    destructive: bool = False,
) -> bool:
    """
    Show a confirmation dialog and return result.

    Args:
        parent: Parent widget
        title: Dialog title
        message: Confirmation message
        confirm_text: Text for confirm button
        destructive: Style as destructive action

    Returns:
        True if user confirmed, False otherwise
    """
    dialog = ConfirmDialog(
        parent,
        title=title,
        message=message,
        confirm_text=confirm_text,
        destructive=destructive,
    )
    return dialog.exec() == QDialog.DialogCode.Accepted


def get_input(
    parent: Optional[QWidget],
    title: str,
    label: str = "",
    *,
    placeholder: str = "",
    default: str = "",
) -> Optional[str]:
    """
    Show an input dialog and return the value.

    Args:
        parent: Parent widget
        title: Dialog title
        label: Input label
        placeholder: Placeholder text
        default: Default value

    Returns:
        Input value if accepted, None if cancelled
    """
    dialog = InputDialog(
        parent,
        title=title,
        label=label,
        placeholder=placeholder,
        default_value=default,
    )
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.value()
    return None
