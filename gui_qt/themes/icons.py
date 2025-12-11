"""
Icon and pixmap utilities for themes.
"""

from pathlib import Path
from typing import Optional

from gui_qt.themes.theme_enum import Theme, THEME_BANNER_MAP


def get_app_icon():
    """Get the application icon as a QIcon."""
    from PyQt6.QtGui import QIcon

    base = Path(__file__).parent.parent.parent / "assets"
    for name in ("icon.png", "icon.ico"):
        path = base / name
        if path.exists():
            return QIcon(str(path))
    return None


def get_app_banner_pixmap(size: int = 180, theme: Optional[Theme] = None):
    """Get the application banner as a scaled QPixmap.

    Args:
        size: Size to scale the banner to
        theme: Theme to get banner for (defaults to current theme)

    Returns:
        QPixmap scaled to the requested size, or None if not found
    """
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt

    from gui_qt.themes.theme_manager import get_theme_manager

    base = Path(__file__).parent.parent.parent / "assets"

    # Get theme-specific banner
    if theme is None:
        theme = get_theme_manager().current_theme

    banner_folder = THEME_BANNER_MAP.get(theme, "default")

    # Try theme-specific banner first
    theme_banner = base / "banners" / banner_folder / "banner_large.png"
    if theme_banner.exists():
        pixmap = QPixmap(str(theme_banner))
        return pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    # Fallback to main banner
    fallback = base / "banner.png"
    if fallback.exists():
        pixmap = QPixmap(str(fallback))
        return pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    return None


def get_theme_icon_pixmap(size: int = 64, theme: Optional[Theme] = None):
    """Get the theme-specific icon as a QPixmap.

    Args:
        size: Size to get (16, 32, 48, 64, or 128)
        theme: Theme to get icon for (defaults to current theme)

    Returns:
        QPixmap at the requested size, or None if not found
    """
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt

    from gui_qt.themes.theme_manager import get_theme_manager

    base = Path(__file__).parent.parent.parent / "assets"

    if theme is None:
        theme = get_theme_manager().current_theme

    banner_folder = THEME_BANNER_MAP.get(theme, "default")

    # Find best size match
    available_sizes = [128, 64, 48, 32, 16]
    target_size = min(available_sizes, key=lambda x: abs(x - size))

    icon_path = base / "banners" / banner_folder / f"icon_{target_size}.png"
    if icon_path.exists():
        pixmap = QPixmap(str(icon_path))
        if pixmap.width() != size:
            return pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        return pixmap

    return None


def apply_window_icon(window):
    """Apply the application icon to a window or dialog."""
    icon = get_app_icon()
    if icon:
        window.setWindowIcon(icon)
