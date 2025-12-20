"""
gui_qt.dialogs.settings_dialog

Dialog for application settings including accessibility, performance, and system tray options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui_qt.styles import apply_window_icon

if TYPE_CHECKING:
    from core.config import Config


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(
        self,
        config: Config,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config = config

        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)
        self.setSizeGripEnabled(True)
        apply_window_icon(self)

        self._create_widgets()
        self._load_settings()
        self._size_to_screen_percent(0.75)
        self._center_on_screen()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Tab widget for different setting categories
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Accessibility tab
        accessibility_tab = self._create_accessibility_tab()
        self._tabs.addTab(accessibility_tab, "Accessibility")

        # Performance tab
        performance_tab = self._create_performance_tab()
        self._tabs.addTab(performance_tab, "Performance")

        # System Tray tab
        tray_tab = self._create_tray_tab()
        self._tabs.addTab(tray_tab, "System Tray")

        # AI tab
        ai_tab = self._create_ai_tab()
        self._tabs.addTab(ai_tab, "AI")

        # Verdict tab
        verdict_tab = self._create_verdict_tab()
        self._tabs.addTab(verdict_tab, "Verdict")

        # Alerts tab
        alerts_tab = self._create_alerts_tab()
        self._tabs.addTab(alerts_tab, "Alerts")

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setToolTip("Reset all settings on the current tab to their default values")
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_row.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_accept)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

    def _create_accessibility_tab(self) -> QWidget:
        """Create the Accessibility settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Font Scaling group
        font_group = QGroupBox("Display")
        font_layout = QVBoxLayout(font_group)
        font_layout.setSpacing(12)

        # Font scale slider
        scale_row = QHBoxLayout()
        scale_label = QLabel("Font scale:")
        scale_row.addWidget(scale_label)

        self._font_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_scale_slider.setRange(80, 150)  # 0.8x to 1.5x
        self._font_scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._font_scale_slider.setTickInterval(10)
        self._font_scale_slider.setToolTip(
            "Scale all fonts in the application.\n"
            "Useful for high-DPI displays or visual accessibility."
        )
        self._font_scale_slider.valueChanged.connect(self._on_font_scale_changed)
        scale_row.addWidget(self._font_scale_slider)

        self._font_scale_label = QLabel("100%")
        self._font_scale_label.setMinimumWidth(45)
        scale_row.addWidget(self._font_scale_label)

        font_layout.addLayout(scale_row)

        # Preset buttons
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))

        for label, value in [("Small", 80), ("Normal", 100), ("Large", 125), ("Extra Large", 150)]:
            btn = QPushButton(label)
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda checked, v=value: self._font_scale_slider.setValue(v))
            preset_row.addWidget(btn)

        preset_row.addStretch()
        font_layout.addLayout(preset_row)

        layout.addWidget(font_group)

        # Timing & Motion group
        timing_group = QGroupBox("Timing & Motion")
        timing_layout = QVBoxLayout(timing_group)
        timing_layout.setSpacing(8)

        # Tooltip delay
        tooltip_row = QHBoxLayout()
        tooltip_row.addWidget(QLabel("Tooltip delay:"))

        self._tooltip_delay_spin = QSpinBox()
        self._tooltip_delay_spin.setRange(100, 2000)
        self._tooltip_delay_spin.setSingleStep(100)
        self._tooltip_delay_spin.setSuffix(" ms")
        self._tooltip_delay_spin.setToolTip(
            "How long to wait before showing tooltips.\n"
            "Increase if tooltips appear too quickly."
        )
        tooltip_row.addWidget(self._tooltip_delay_spin)
        tooltip_row.addStretch()
        timing_layout.addLayout(tooltip_row)

        # Reduce animations
        self._reduce_animations_cb = QCheckBox("Reduce animations")
        self._reduce_animations_cb.setToolTip(
            "Disable or reduce motion effects in the interface.\n"
            "Recommended for users sensitive to motion."
        )
        timing_layout.addWidget(self._reduce_animations_cb)

        layout.addWidget(timing_group)

        # Info text
        info_label = QLabel(
            "Note: Font scaling changes require restarting the application to take full effect."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()
        return tab

    def _create_performance_tab(self) -> QWidget:
        """Create the Performance settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Cache Settings group
        cache_group = QGroupBox("Cache Settings")
        cache_layout = QVBoxLayout(cache_group)
        cache_layout.setSpacing(12)

        # Rankings cache
        rankings_row = QHBoxLayout()
        rankings_label = QLabel("Top 20 rankings staleness:")
        rankings_label.setToolTip(
            "How long to cache price rankings before refreshing.\n"
            "Lower = fresher data but more API calls."
        )
        rankings_row.addWidget(rankings_label)

        self._rankings_cache_spin = QSpinBox()
        self._rankings_cache_spin.setRange(1, 168)  # 1 hour to 1 week
        self._rankings_cache_spin.setSuffix(" hours")
        self._rankings_cache_spin.setToolTip(
            "Min: 1 hour, Max: 168 hours (1 week)\n"
            "Recommended: 24 hours for daily fresh data"
        )
        rankings_row.addWidget(self._rankings_cache_spin)
        rankings_row.addStretch()
        cache_layout.addLayout(rankings_row)

        # Price cache TTL
        price_cache_row = QHBoxLayout()
        price_cache_label = QLabel("Price data cache:")
        price_cache_label.setToolTip(
            "How long to cache individual price lookups.\n"
            "Affects how often the app queries external APIs."
        )
        price_cache_row.addWidget(price_cache_label)

        self._price_cache_combo = QComboBox()
        self._price_cache_combo.addItem("5 minutes (frequent updates)", 300)
        self._price_cache_combo.addItem("15 minutes", 900)
        self._price_cache_combo.addItem("30 minutes", 1800)
        self._price_cache_combo.addItem("1 hour (recommended)", 3600)
        self._price_cache_combo.addItem("2 hours (conservative)", 7200)
        self._price_cache_combo.setToolTip(
            "Shorter = more up-to-date prices\n"
            "Longer = fewer API calls, less risk of rate limiting"
        )
        price_cache_row.addWidget(self._price_cache_combo)
        price_cache_row.addStretch()
        cache_layout.addLayout(price_cache_row)

        layout.addWidget(cache_group)

        # API Settings group
        api_group = QGroupBox("API Rate Limiting")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(8)

        # Warning label
        warning_label = QLabel(
            "⚠️ GGG enforces strict rate limits. Setting values too aggressive\n"
            "   may result in temporary API bans (429 errors)."
        )
        warning_label.setStyleSheet("color: #e67e22; font-size: 11px;")
        api_layout.addWidget(warning_label)

        # Rate limit slider
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("API request rate:"))

        self._rate_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self._rate_limit_slider.setRange(20, 100)  # 0.2 to 1.0 req/s
        self._rate_limit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._rate_limit_slider.setTickInterval(20)
        self._rate_limit_slider.valueChanged.connect(self._on_rate_limit_changed)
        self._rate_limit_slider.setToolTip(
            "How fast to send API requests.\n"
            "Conservative (left) = safer, slower\n"
            "Aggressive (right) = faster, may hit limits"
        )
        rate_row.addWidget(self._rate_limit_slider)

        self._rate_limit_label = QLabel("1 req/3s")
        self._rate_limit_label.setMinimumWidth(70)
        rate_row.addWidget(self._rate_limit_label)

        api_layout.addLayout(rate_row)

        # Rate limit descriptions
        rate_desc_row = QHBoxLayout()
        rate_desc_row.addWidget(QLabel("Conservative"))
        rate_desc_row.addStretch()
        rate_desc_row.addWidget(QLabel("Aggressive"))
        api_layout.addLayout(rate_desc_row)

        layout.addWidget(api_group)

        # UI Settings group
        ui_group = QGroupBox("UI Feedback")
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setSpacing(8)

        # Toast duration
        toast_row = QHBoxLayout()
        toast_row.addWidget(QLabel("Toast notification duration:"))

        self._toast_duration_spin = QSpinBox()
        self._toast_duration_spin.setRange(1000, 10000)
        self._toast_duration_spin.setSingleStep(500)
        self._toast_duration_spin.setSuffix(" ms")
        self._toast_duration_spin.setToolTip(
            "How long toast notifications remain visible.\n"
            "Default: 3000ms (3 seconds)"
        )
        toast_row.addWidget(self._toast_duration_spin)
        toast_row.addStretch()
        ui_layout.addLayout(toast_row)

        # History entries
        history_row = QHBoxLayout()
        history_row.addWidget(QLabel("History entries to keep:"))

        self._history_max_spin = QSpinBox()
        self._history_max_spin.setRange(10, 500)
        self._history_max_spin.setSingleStep(10)
        self._history_max_spin.setToolTip(
            "Maximum number of price check history entries.\n"
            "Higher = more memory usage"
        )
        history_row.addWidget(self._history_max_spin)
        history_row.addStretch()
        ui_layout.addLayout(history_row)

        layout.addWidget(ui_group)

        layout.addStretch()
        return tab

    def _create_tray_tab(self) -> QWidget:
        """Create the System Tray settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Tray Behavior group
        behavior_group = QGroupBox("Tray Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        behavior_layout.setSpacing(8)

        self._minimize_to_tray_cb = QCheckBox("Minimize button hides to tray")
        self._minimize_to_tray_cb.setToolTip(
            "When enabled, the minimize button will hide to system tray.\n"
            "When disabled, use File > Minimize to Tray for explicit tray minimize.\n"
            "Click the tray icon to restore the window."
        )
        behavior_layout.addWidget(self._minimize_to_tray_cb)

        self._start_minimized_cb = QCheckBox("Start minimized to tray")
        self._start_minimized_cb.setToolTip(
            "When enabled, the application will start minimized to the system tray.\n"
            "Useful if you want it running in the background at startup."
        )
        behavior_layout.addWidget(self._start_minimized_cb)

        layout.addWidget(behavior_group)

        # Notifications group
        notif_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif_group)
        notif_layout.setSpacing(8)

        self._show_notifications_cb = QCheckBox("Show price alert notifications")
        self._show_notifications_cb.setToolTip(
            "When enabled, system notifications will appear when\n"
            "high-value items are detected during price checks."
        )
        self._show_notifications_cb.stateChanged.connect(self._on_notifications_toggled)
        notif_layout.addWidget(self._show_notifications_cb)

        # Threshold row
        threshold_row = QHBoxLayout()
        threshold_row.setSpacing(8)

        threshold_label = QLabel("Alert threshold:")
        threshold_row.addWidget(threshold_label)

        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0, 999999)
        self._threshold_spin.setDecimals(0)
        self._threshold_spin.setSuffix(" chaos")
        self._threshold_spin.setToolTip(
            "Items worth more than this value will trigger a notification.\n"
            "Set to 0 to be notified for all items."
        )
        self._threshold_spin.setMinimumWidth(120)
        threshold_row.addWidget(self._threshold_spin)

        threshold_row.addStretch()
        notif_layout.addLayout(threshold_row)

        # Help text
        help_label = QLabel(
            "Notifications appear in your system tray when checking items\n"
            "that exceed the threshold value."
        )
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        notif_layout.addWidget(help_label)

        layout.addWidget(notif_group)

        layout.addStretch()
        return tab

    def _create_ai_tab(self) -> QWidget:
        """Create the AI settings tab with scroll area for content."""
        from data_sources.ai import SUPPORTED_PROVIDERS, get_provider_display_name

        # Create scroll area as the main container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Content widget inside scroll area
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 12, 20, 12)  # Add padding, extra right for scrollbar

        # Provider Selection group
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout(provider_group)
        provider_layout.setSpacing(12)

        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider:"))

        self._ai_provider_combo = QComboBox()
        self._ai_provider_combo.addItem("None (Disabled)", "")
        for provider in SUPPORTED_PROVIDERS:
            display_name = get_provider_display_name(provider)
            self._ai_provider_combo.addItem(display_name, provider)

        self._ai_provider_combo.setToolTip(
            "Select the AI provider to use for item analysis.\n"
            "Cloud providers require API keys. Ollama runs locally."
        )
        self._ai_provider_combo.currentIndexChanged.connect(self._on_ai_provider_changed)
        provider_row.addWidget(self._ai_provider_combo)
        provider_row.addStretch()
        provider_layout.addLayout(provider_row)

        layout.addWidget(provider_group)

        # API Keys group
        keys_group = QGroupBox("API Keys")
        self._keys_group = keys_group
        keys_layout = QVBoxLayout(keys_group)
        keys_layout.setSpacing(12)

        info_label = QLabel(
            "Enter your API key for the selected provider.\n"
            "Keys are stored encrypted on your local machine."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        keys_layout.addWidget(info_label)

        # Gemini API key
        gemini_row = QHBoxLayout()
        gemini_label = QLabel("Gemini:")
        gemini_label.setMinimumWidth(70)
        gemini_row.addWidget(gemini_label)
        self._gemini_key_edit = QLineEdit()
        self._gemini_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._gemini_key_edit.setPlaceholderText("Enter Gemini API key")
        self._gemini_key_edit.setToolTip("Get a free key from ai.google.dev")
        self._gemini_key_edit.setMaximumWidth(400)
        gemini_row.addWidget(self._gemini_key_edit)
        gemini_row.addStretch()
        keys_layout.addLayout(gemini_row)

        # Claude API key
        claude_row = QHBoxLayout()
        claude_label = QLabel("Claude:")
        claude_label.setMinimumWidth(70)
        claude_row.addWidget(claude_label)
        self._claude_key_edit = QLineEdit()
        self._claude_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._claude_key_edit.setPlaceholderText("Enter Claude API key")
        self._claude_key_edit.setToolTip("Get a key from console.anthropic.com")
        self._claude_key_edit.setMaximumWidth(400)
        claude_row.addWidget(self._claude_key_edit)
        claude_row.addStretch()
        keys_layout.addLayout(claude_row)

        # OpenAI API key
        openai_row = QHBoxLayout()
        openai_label = QLabel("OpenAI:")
        openai_label.setMinimumWidth(70)
        openai_row.addWidget(openai_label)
        self._openai_key_edit = QLineEdit()
        self._openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._openai_key_edit.setPlaceholderText("Enter OpenAI API key")
        self._openai_key_edit.setToolTip("Get a key from platform.openai.com")
        self._openai_key_edit.setMaximumWidth(400)
        openai_row.addWidget(self._openai_key_edit)
        openai_row.addStretch()
        keys_layout.addLayout(openai_row)

        # Groq API key
        groq_row = QHBoxLayout()
        groq_label = QLabel("Groq:")
        groq_label.setMinimumWidth(70)
        groq_row.addWidget(groq_label)
        self._groq_key_edit = QLineEdit()
        self._groq_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_key_edit.setPlaceholderText("Enter Groq API key (free tier available)")
        self._groq_key_edit.setToolTip("Get a free key from console.groq.com")
        self._groq_key_edit.setMaximumWidth(400)
        groq_row.addWidget(self._groq_key_edit)
        groq_row.addStretch()
        keys_layout.addLayout(groq_row)

        # xAI API key
        xai_row = QHBoxLayout()
        xai_label = QLabel("xAI Grok:")
        xai_label.setMinimumWidth(70)
        xai_row.addWidget(xai_label)
        self._xai_key_edit = QLineEdit()
        self._xai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._xai_key_edit.setPlaceholderText("Enter xAI API key")
        self._xai_key_edit.setToolTip("Get a key from console.x.ai")
        self._xai_key_edit.setMaximumWidth(400)
        xai_row.addWidget(self._xai_key_edit)
        xai_row.addStretch()
        keys_layout.addLayout(xai_row)

        layout.addWidget(keys_group)

        # Ollama Settings group (local LLM)
        ollama_group = QGroupBox("Ollama Settings (Local LLM)")
        self._ollama_group = ollama_group
        ollama_layout = QVBoxLayout(ollama_group)
        ollama_layout.setSpacing(8)

        ollama_info = QLabel(
            "Ollama runs LLMs locally - no API key needed.\n"
            "Install from ollama.ai, then: ollama pull llama3.1:8b"
        )
        ollama_info.setStyleSheet("color: gray; font-size: 11px;")
        ollama_layout.addWidget(ollama_info)

        # Ollama host
        host_row = QHBoxLayout()
        host_label = QLabel("Host:")
        host_label.setMinimumWidth(70)
        host_row.addWidget(host_label)
        self._ollama_host_edit = QLineEdit()
        self._ollama_host_edit.setPlaceholderText("http://localhost:11434")
        self._ollama_host_edit.setToolTip("Ollama server URL (default: http://localhost:11434)")
        self._ollama_host_edit.setMaximumWidth(300)
        host_row.addWidget(self._ollama_host_edit)
        host_row.addStretch()
        ollama_layout.addLayout(host_row)

        # Ollama model
        model_row = QHBoxLayout()
        model_label = QLabel("Model:")
        model_label.setMinimumWidth(70)
        model_row.addWidget(model_label)
        self._ollama_model_combo = QComboBox()
        self._ollama_model_combo.setEditable(True)
        self._ollama_model_combo.setMaximumWidth(250)
        self._ollama_model_combo.addItems([
            "deepseek-r1:70b",
            "deepseek-r1:32b",
            "deepseek-r1:14b",
            "deepseek-r1:8b",
            "qwen2.5:72b",
            "qwen2.5:32b",
            "qwen2.5:14b",
            "llama3.3:70b",
            "gemma3:27b",
            "mistral:7b",
        ])
        self._ollama_model_combo.setToolTip(
            "Select or type an Ollama model name.\n"
            "Ensure the model is pulled: ollama pull <model>"
        )
        model_row.addWidget(self._ollama_model_combo)
        model_row.addStretch()
        ollama_layout.addLayout(model_row)

        layout.addWidget(ollama_group)

        # Build Context group
        context_group = QGroupBox("Context")
        context_layout = QVBoxLayout(context_group)
        context_layout.setSpacing(8)

        # Build name
        build_row = QHBoxLayout()
        build_label = QLabel("My build:")
        build_label.setMinimumWidth(70)
        build_row.addWidget(build_label)
        self._ai_build_edit = QLineEdit()
        self._ai_build_edit.setPlaceholderText("e.g., Lightning Arrow Deadeye, RF Chieftain")
        self._ai_build_edit.setToolTip(
            "Your current build name. This helps AI give relevant advice.\n"
            "Examples: 'Tornado Shot MF', 'Righteous Fire Juggernaut'"
        )
        self._ai_build_edit.setMaximumWidth(400)
        build_row.addWidget(self._ai_build_edit)
        build_row.addStretch()
        context_layout.addLayout(build_row)

        context_note = QLabel(
            "The current league is automatically included from your settings."
        )
        context_note.setStyleSheet("color: gray; font-size: 10px;")
        context_layout.addWidget(context_note)

        layout.addWidget(context_group)

        # Settings group
        settings_group = QGroupBox("Response Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(8)

        # Max tokens
        tokens_row = QHBoxLayout()
        tokens_row.addWidget(QLabel("Max response tokens:"))
        self._ai_max_tokens_spin = QSpinBox()
        self._ai_max_tokens_spin.setRange(100, 2000)
        self._ai_max_tokens_spin.setSingleStep(100)
        self._ai_max_tokens_spin.setToolTip(
            "Maximum tokens in AI response.\n"
            "Higher = longer responses, more cost"
        )
        tokens_row.addWidget(self._ai_max_tokens_spin)
        tokens_row.addStretch()
        settings_layout.addLayout(tokens_row)

        # Timeout
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Request timeout:"))
        self._ai_timeout_spin = QSpinBox()
        self._ai_timeout_spin.setRange(10, 300)
        self._ai_timeout_spin.setSuffix(" seconds")
        self._ai_timeout_spin.setToolTip(
            "How long to wait for AI response.\n"
            "Local models (Ollama) need 120-300s for large models.\n"
            "Cloud APIs typically respond in 10-30s."
        )
        timeout_row.addWidget(self._ai_timeout_spin)
        timeout_row.addStretch()
        settings_layout.addLayout(timeout_row)

        layout.addWidget(settings_group)

        # Custom Prompt group
        prompt_group = QGroupBox("Custom Prompt (Advanced)")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(8)

        prompt_info = QLabel(
            "Customize the prompt sent to AI. Leave empty to use the default.\n"
            "Placeholders: {item_text}, {price_context}, {league}, {build_name}"
        )
        prompt_info.setStyleSheet("color: gray; font-size: 10px;")
        prompt_layout.addWidget(prompt_info)

        self._ai_prompt_edit = QPlainTextEdit()
        self._ai_prompt_edit.setPlaceholderText(
            "Leave empty to use the default prompt.\n\n"
            "Example custom prompt:\n"
            "I'm playing {build_name} in {league} league.\n\n"
            "Analyze this item:\n{item_text}\n\n"
            "Price info: {price_context}\n\n"
            "Is this item good for my build? What's it worth?"
        )
        self._ai_prompt_edit.setMinimumHeight(120)
        self._ai_prompt_edit.setMaximumHeight(200)
        prompt_layout.addWidget(self._ai_prompt_edit)

        # Reset button
        reset_btn = QPushButton("Reset to Default")
        reset_btn.setToolTip("Clear custom prompt and use the default")
        reset_btn.clicked.connect(lambda: self._ai_prompt_edit.clear())
        reset_btn.setMaximumWidth(120)
        prompt_layout.addWidget(reset_btn)

        layout.addWidget(prompt_group)

        # Usage note
        usage_label = QLabel(
            "Usage: Right-click an item in the results table and select\n"
            "'Ask AI About This Item' to get an AI-powered analysis."
        )
        usage_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(usage_label)

        # Push content to top when dialog is large
        layout.addStretch()

        # Set content in scroll area and return
        scroll.setWidget(content)
        return scroll

    def _on_ai_provider_changed(self, index: int) -> None:
        """Handle AI provider combo box change."""
        # Could be used to highlight the relevant API key field
        pass

    def _create_verdict_tab(self) -> QWidget:
        """Create the Verdict settings tab for keep/vendor thresholds."""

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Thresholds group
        thresholds_group = QGroupBox("Verdict Thresholds")
        thresholds_layout = QVBoxLayout(thresholds_group)
        thresholds_layout.setSpacing(12)

        info_label = QLabel(
            "Configure chaos value thresholds for Quick Verdict decisions.\n"
            "Items below Vendor threshold = 👎 VENDOR\n"
            "Items above Keep threshold = 👍 KEEP\n"
            "Items between = 🤔 MAYBE"
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        thresholds_layout.addWidget(info_label)

        # Vendor threshold
        vendor_row = QHBoxLayout()
        vendor_label = QLabel("Vendor threshold:")
        vendor_label.setMinimumWidth(120)
        vendor_row.addWidget(vendor_label)

        self._vendor_threshold_spin = QDoubleSpinBox()
        self._vendor_threshold_spin.setRange(0.1, 50.0)
        self._vendor_threshold_spin.setSingleStep(0.5)
        self._vendor_threshold_spin.setSuffix(" chaos")
        self._vendor_threshold_spin.setToolTip(
            "Items with value below this threshold will be marked as VENDOR.\n"
            "Default: 2.0 chaos"
        )
        self._vendor_threshold_spin.valueChanged.connect(self._on_verdict_threshold_changed)
        vendor_row.addWidget(self._vendor_threshold_spin)
        vendor_row.addStretch()
        thresholds_layout.addLayout(vendor_row)

        # Keep threshold
        keep_row = QHBoxLayout()
        keep_label = QLabel("Keep threshold:")
        keep_label.setMinimumWidth(120)
        keep_row.addWidget(keep_label)

        self._keep_threshold_spin = QDoubleSpinBox()
        self._keep_threshold_spin.setRange(1.0, 500.0)
        self._keep_threshold_spin.setSingleStep(1.0)
        self._keep_threshold_spin.setSuffix(" chaos")
        self._keep_threshold_spin.setToolTip(
            "Items with value above this threshold will be marked as KEEP.\n"
            "Default: 15.0 chaos"
        )
        self._keep_threshold_spin.valueChanged.connect(self._on_verdict_threshold_changed)
        keep_row.addWidget(self._keep_threshold_spin)
        keep_row.addStretch()
        thresholds_layout.addLayout(keep_row)

        layout.addWidget(thresholds_group)

        # Presets group
        presets_group = QGroupBox("League Timing Presets")
        presets_layout = QVBoxLayout(presets_group)
        presets_layout.setSpacing(12)

        preset_info = QLabel(
            "Use presets based on league timing. Early league keeps more items,\n"
            "late league is more selective. SSF mode keeps anything useful."
        )
        preset_info.setStyleSheet("color: gray; font-size: 11px;")
        presets_layout.addWidget(preset_info)

        # Preset buttons
        preset_btn_row = QHBoxLayout()

        presets = [
            ("League Start", "league_start", "Very lenient - keep more items (1c vendor, 5c keep)"),
            ("Mid League", "mid_league", "Balanced thresholds (2c vendor, 10c keep)"),
            ("Late League", "late_league", "More selective (5c vendor, 20c keep)"),
            ("SSF", "ssf", "Keep anything useful (0.5c vendor, 3c keep)"),
        ]

        for label, preset_id, tooltip in presets:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, p=preset_id: self._apply_verdict_preset(p))
            preset_btn_row.addWidget(btn)

        preset_btn_row.addStretch()
        presets_layout.addLayout(preset_btn_row)

        # Current preset label
        self._preset_label = QLabel("Current preset: Default")
        self._preset_label.setStyleSheet("font-style: italic;")
        presets_layout.addWidget(self._preset_label)

        layout.addWidget(presets_group)

        # Push content to top
        layout.addStretch()

        return tab

    def _create_alerts_tab(self) -> QWidget:
        """Create the Price Alerts settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Enable/Disable group
        enable_group = QGroupBox("Price Alert Monitoring")
        enable_layout = QVBoxLayout(enable_group)
        enable_layout.setSpacing(8)

        self._alerts_enabled_cb = QCheckBox("Enable price alerts")
        self._alerts_enabled_cb.setToolTip(
            "When enabled, the app will periodically check prices\n"
            "for items in your alert list and notify you when\n"
            "prices cross your configured thresholds."
        )
        self._alerts_enabled_cb.stateChanged.connect(self._on_alerts_enabled_changed)
        enable_layout.addWidget(self._alerts_enabled_cb)

        info_label = QLabel(
            "Create alerts via View > Price Alerts or right-click\n"
            "an item in the results table."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        enable_layout.addWidget(info_label)

        layout.addWidget(enable_group)

        # Polling Settings group
        polling_group = QGroupBox("Polling Settings")
        self._polling_group = polling_group
        polling_layout = QVBoxLayout(polling_group)
        polling_layout.setSpacing(12)

        # Polling interval
        interval_row = QHBoxLayout()
        interval_label = QLabel("Check interval:")
        interval_label.setMinimumWidth(120)
        interval_row.addWidget(interval_label)

        self._alert_interval_spin = QSpinBox()
        self._alert_interval_spin.setRange(5, 60)
        self._alert_interval_spin.setSuffix(" minutes")
        self._alert_interval_spin.setToolTip(
            "How often to check prices for active alerts.\n"
            "Min: 5 minutes, Max: 60 minutes\n"
            "Lower = more up-to-date but more API calls"
        )
        interval_row.addWidget(self._alert_interval_spin)
        interval_row.addStretch()
        polling_layout.addLayout(interval_row)

        # Default cooldown
        cooldown_row = QHBoxLayout()
        cooldown_label = QLabel("Default cooldown:")
        cooldown_label.setMinimumWidth(120)
        cooldown_row.addWidget(cooldown_label)

        self._alert_cooldown_spin = QSpinBox()
        self._alert_cooldown_spin.setRange(10, 1440)
        self._alert_cooldown_spin.setSuffix(" minutes")
        self._alert_cooldown_spin.setToolTip(
            "Default time to wait after an alert triggers\n"
            "before it can trigger again.\n"
            "Prevents notification spam for volatile prices."
        )
        cooldown_row.addWidget(self._alert_cooldown_spin)
        cooldown_row.addStretch()
        polling_layout.addLayout(cooldown_row)

        layout.addWidget(polling_group)

        # Notification Settings group
        notif_group = QGroupBox("Notification Settings")
        self._alert_notif_group = notif_group
        notif_layout = QVBoxLayout(notif_group)
        notif_layout.setSpacing(8)

        self._alert_tray_cb = QCheckBox("Show system tray notifications")
        self._alert_tray_cb.setToolTip(
            "When enabled, triggered alerts will show\n"
            "a notification in your system tray."
        )
        notif_layout.addWidget(self._alert_tray_cb)

        self._alert_toast_cb = QCheckBox("Show in-app toast notifications")
        self._alert_toast_cb.setToolTip(
            "When enabled, triggered alerts will show\n"
            "a toast notification inside the app."
        )
        notif_layout.addWidget(self._alert_toast_cb)

        layout.addWidget(notif_group)

        # Manage Alerts button
        manage_row = QHBoxLayout()
        manage_row.addStretch()

        self._manage_alerts_btn = QPushButton("Manage Alerts...")
        self._manage_alerts_btn.setToolTip("Open the Price Alerts management dialog")
        self._manage_alerts_btn.clicked.connect(self._open_alerts_dialog)
        manage_row.addWidget(self._manage_alerts_btn)

        layout.addLayout(manage_row)

        # Push content to top
        layout.addStretch()

        return tab

    def _on_alerts_enabled_changed(self) -> None:
        """Handle alerts enabled checkbox change."""
        enabled = self._alerts_enabled_cb.isChecked()
        self._polling_group.setEnabled(enabled)
        self._alert_notif_group.setEnabled(enabled)

    def _open_alerts_dialog(self) -> None:
        """Open the price alerts management dialog."""
        from gui_qt.services import get_price_alert_service

        # Get the alert service (may not be initialized yet)
        service = get_price_alert_service()
        if service:
            from gui_qt.dialogs.price_alerts_dialog import PriceAlertsDialog
            dialog = PriceAlertsDialog(service, self)
            dialog.exec()

    def _apply_verdict_preset(self, preset: str) -> None:
        """Apply a verdict threshold preset."""
        from core.quick_verdict import VerdictThresholds

        preset_map = {
            "league_start": VerdictThresholds.for_league_start(),
            "mid_league": VerdictThresholds.for_mid_league(),
            "late_league": VerdictThresholds.for_late_league(),
            "ssf": VerdictThresholds.for_ssf(),
        }

        if preset in preset_map:
            thresholds = preset_map[preset]
            self._vendor_threshold_spin.setValue(thresholds.vendor_threshold)
            self._keep_threshold_spin.setValue(thresholds.keep_threshold)

            preset_names = {
                "league_start": "League Start",
                "mid_league": "Mid League",
                "late_league": "Late League",
                "ssf": "SSF",
            }
            self._preset_label.setText(f"Current preset: {preset_names.get(preset, preset)}")

    def _on_font_scale_changed(self, value: int) -> None:
        """Update font scale label when slider changes."""
        self._font_scale_label.setText(f"{value}%")

    def _on_rate_limit_changed(self, value: int) -> None:
        """Update rate limit label when slider changes."""
        rate = value / 100.0  # Convert to req/s
        if rate <= 0.25:
            self._rate_limit_label.setText(f"1 req/{int(1/rate)}s")
        elif rate < 1.0:
            self._rate_limit_label.setText(f"1 req/{1/rate:.1f}s")
        else:
            self._rate_limit_label.setText("1 req/s")

    def _on_notifications_toggled(self) -> None:
        """Handle notifications checkbox state change."""
        enabled = self._show_notifications_cb.isChecked()
        self._threshold_spin.setEnabled(enabled)

    def _on_verdict_threshold_changed(self) -> None:
        """Handle manual change to verdict threshold spinboxes."""
        # When user manually edits thresholds, mark as Custom preset
        if hasattr(self, '_preset_label'):
            self._preset_label.setText("Current preset: Custom")

    def _load_settings(self) -> None:
        """Load current settings into the widgets."""
        # Accessibility
        self._font_scale_slider.setValue(int(self._config.font_scale * 100))
        self._tooltip_delay_spin.setValue(self._config.tooltip_delay_ms)
        self._reduce_animations_cb.setChecked(self._config.reduce_animations)

        # Performance
        self._rankings_cache_spin.setValue(self._config.rankings_cache_hours)

        # Find matching price cache combo item
        price_ttl = self._config.price_cache_ttl_seconds
        for i in range(self._price_cache_combo.count()):
            if self._price_cache_combo.itemData(i) == price_ttl:
                self._price_cache_combo.setCurrentIndex(i)
                break
        else:
            # Default to 1 hour if not found
            self._price_cache_combo.setCurrentIndex(3)

        self._rate_limit_slider.setValue(int(self._config.api_rate_limit * 100))
        self._toast_duration_spin.setValue(self._config.toast_duration_ms)
        self._history_max_spin.setValue(self._config.history_max_entries)

        # System Tray
        self._minimize_to_tray_cb.setChecked(self._config.minimize_to_tray)
        self._start_minimized_cb.setChecked(self._config.start_minimized)
        self._show_notifications_cb.setChecked(self._config.show_tray_notifications)
        self._threshold_spin.setValue(self._config.tray_alert_threshold)

        # AI
        # Find matching provider in combo
        current_provider = self._config.ai_provider
        for i in range(self._ai_provider_combo.count()):
            if self._ai_provider_combo.itemData(i) == current_provider:
                self._ai_provider_combo.setCurrentIndex(i)
                break

        # Load API keys - show placeholder if set (don't expose actual key)
        if self._config.get_ai_api_key("gemini"):
            self._gemini_key_edit.setText("••••••••••••••••")
        if self._config.get_ai_api_key("claude"):
            self._claude_key_edit.setText("••••••••••••••••")
        if self._config.get_ai_api_key("openai"):
            self._openai_key_edit.setText("••••••••••••••••")
        if self._config.get_ai_api_key("groq"):
            self._groq_key_edit.setText("••••••••••••••••")
        if self._config.get_ai_api_key("xai"):
            self._xai_key_edit.setText("••••••••••••••••")

        # Ollama settings
        ollama_host = getattr(self._config, "ollama_host", "")
        self._ollama_host_edit.setText(ollama_host)
        ollama_model = getattr(self._config, "ollama_model", "llama3.1:8b")
        idx = self._ollama_model_combo.findText(ollama_model)
        if idx >= 0:
            self._ollama_model_combo.setCurrentIndex(idx)
        else:
            self._ollama_model_combo.setCurrentText(ollama_model)

        self._ai_max_tokens_spin.setValue(self._config.ai_max_tokens)
        self._ai_timeout_spin.setValue(self._config.ai_timeout)
        self._ai_build_edit.setText(self._config.ai_build_name)
        self._ai_prompt_edit.setPlainText(self._config.ai_custom_prompt)

        # Verdict
        self._vendor_threshold_spin.setValue(self._config.verdict_vendor_threshold)
        self._keep_threshold_spin.setValue(self._config.verdict_keep_threshold)
        preset = self._config.verdict_preset
        if preset and preset != "default":
            preset_names = {
                "league_start": "League Start",
                "mid_league": "Mid League",
                "late_league": "Late League",
                "ssf": "SSF",
            }
            self._preset_label.setText(f"Current preset: {preset_names.get(preset, preset)}")
        else:
            self._preset_label.setText("Current preset: Custom")

        # Alerts
        self._alerts_enabled_cb.setChecked(self._config.alerts_enabled)
        self._alert_interval_spin.setValue(self._config.alert_polling_interval_minutes)
        self._alert_cooldown_spin.setValue(self._config.alert_default_cooldown_minutes)
        self._alert_tray_cb.setChecked(self._config.alert_show_tray_notifications)
        self._alert_toast_cb.setChecked(self._config.alert_show_toast_notifications)

        # Update dependent states
        self._on_font_scale_changed(self._font_scale_slider.value())
        self._on_rate_limit_changed(self._rate_limit_slider.value())
        self._on_notifications_toggled()
        self._on_alerts_enabled_changed()

    def _reset_to_defaults(self) -> None:
        """Reset settings to their default values based on current tab."""
        current_tab = self._tabs.currentIndex()

        if current_tab == 0:  # Accessibility
            self._font_scale_slider.setValue(100)
            self._tooltip_delay_spin.setValue(500)
            self._reduce_animations_cb.setChecked(False)
        elif current_tab == 1:  # Performance
            self._rankings_cache_spin.setValue(24)
            self._price_cache_combo.setCurrentIndex(3)  # 1 hour
            self._rate_limit_slider.setValue(33)  # 0.33 req/s
            self._toast_duration_spin.setValue(3000)
            self._history_max_spin.setValue(100)
        elif current_tab == 2:  # System Tray
            self._minimize_to_tray_cb.setChecked(False)  # Use File > Minimize to Tray instead
            self._start_minimized_cb.setChecked(False)
            self._show_notifications_cb.setChecked(True)
            self._threshold_spin.setValue(50.0)
            self._on_notifications_toggled()
        elif current_tab == 3:  # AI
            self._ai_provider_combo.setCurrentIndex(0)  # None
            self._ai_max_tokens_spin.setValue(500)
            self._ai_timeout_spin.setValue(30)
            self._ai_build_edit.clear()
            self._ai_prompt_edit.clear()
        elif current_tab == 4:  # Verdict
            self._vendor_threshold_spin.setValue(2.0)
            self._keep_threshold_spin.setValue(15.0)
            self._preset_label.setText("Current preset: Default")
        elif current_tab == 5:  # Alerts
            self._alerts_enabled_cb.setChecked(True)
            self._alert_interval_spin.setValue(15)
            self._alert_cooldown_spin.setValue(30)
            self._alert_tray_cb.setChecked(True)
            self._alert_toast_cb.setChecked(True)
            self._on_alerts_enabled_changed()

    def _save_and_accept(self) -> None:
        """Save settings and close the dialog."""
        # Accessibility
        self._config.font_scale = self._font_scale_slider.value() / 100.0
        self._config.tooltip_delay_ms = self._tooltip_delay_spin.value()
        self._config.reduce_animations = self._reduce_animations_cb.isChecked()

        # Performance
        self._config.rankings_cache_hours = self._rankings_cache_spin.value()
        self._config.price_cache_ttl_seconds = self._price_cache_combo.currentData()
        self._config.api_rate_limit = self._rate_limit_slider.value() / 100.0
        self._config.toast_duration_ms = self._toast_duration_spin.value()
        self._config.history_max_entries = self._history_max_spin.value()

        # System Tray
        self._config.minimize_to_tray = self._minimize_to_tray_cb.isChecked()
        self._config.start_minimized = self._start_minimized_cb.isChecked()
        self._config.show_tray_notifications = self._show_notifications_cb.isChecked()
        self._config.tray_alert_threshold = self._threshold_spin.value()

        # AI
        self._config.ai_provider = self._ai_provider_combo.currentData() or ""

        # Only save API keys if they were changed (not placeholder text)
        gemini_key = self._gemini_key_edit.text()
        if gemini_key and gemini_key != "••••••••••••••••":
            self._config.set_ai_api_key("gemini", gemini_key)

        claude_key = self._claude_key_edit.text()
        if claude_key and claude_key != "••••••••••••••••":
            self._config.set_ai_api_key("claude", claude_key)

        openai_key = self._openai_key_edit.text()
        if openai_key and openai_key != "••••••••••••••••":
            self._config.set_ai_api_key("openai", openai_key)

        groq_key = self._groq_key_edit.text()
        if groq_key and groq_key != "••••••••••••••••":
            self._config.set_ai_api_key("groq", groq_key)

        xai_key = self._xai_key_edit.text()
        if xai_key and xai_key != "••••••••••••••••":
            self._config.set_ai_api_key("xai", xai_key)

        # Ollama settings
        self._config.ollama_host = self._ollama_host_edit.text().strip()
        self._config.ollama_model = self._ollama_model_combo.currentText().strip()

        self._config.ai_max_tokens = self._ai_max_tokens_spin.value()
        self._config.ai_timeout = self._ai_timeout_spin.value()
        self._config.ai_build_name = self._ai_build_edit.text()
        self._config.ai_custom_prompt = self._ai_prompt_edit.toPlainText()

        # Verdict
        self._config.verdict_vendor_threshold = self._vendor_threshold_spin.value()
        self._config.verdict_keep_threshold = self._keep_threshold_spin.value()
        # Determine preset based on current values
        preset_text = self._preset_label.text()
        if "League Start" in preset_text:
            self._config.verdict_preset = "league_start"
        elif "Mid League" in preset_text:
            self._config.verdict_preset = "mid_league"
        elif "Late League" in preset_text:
            self._config.verdict_preset = "late_league"
        elif "SSF" in preset_text:
            self._config.verdict_preset = "ssf"
        else:
            self._config.verdict_preset = "custom"

        # Alerts
        self._config.alerts_enabled = self._alerts_enabled_cb.isChecked()
        self._config.alert_polling_interval_minutes = self._alert_interval_spin.value()
        self._config.alert_default_cooldown_minutes = self._alert_cooldown_spin.value()
        self._config.alert_show_tray_notifications = self._alert_tray_cb.isChecked()
        self._config.alert_show_toast_notifications = self._alert_toast_cb.isChecked()

        self.accept()

    def _size_to_screen_percent(self, percent: float = 0.75) -> None:
        """Resize the dialog to a percentage of the screen size.

        Args:
            percent: Fraction of screen size (0.0-1.0). Default 0.75 (75%).
        """
        parent = self.parent()
        if parent and hasattr(parent, 'screen') and parent.screen():
            screen = parent.screen()
        else:
            screen = QGuiApplication.primaryScreen()

        if screen:
            screen_geometry = screen.availableGeometry()
            width = int(screen_geometry.width() * percent)
            height = int(screen_geometry.height() * percent)
            self.resize(width, height)

    def _center_on_screen(self) -> None:
        """Center the dialog on the same screen as the parent window."""
        # Use parent window's screen if available, otherwise primary screen
        parent = self.parent()
        if parent and hasattr(parent, 'screen') and parent.screen():
            screen = parent.screen()
        else:
            screen = QGuiApplication.primaryScreen()

        if screen:
            screen_geometry = screen.availableGeometry()
            dialog_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            dialog_geometry.moveCenter(center_point)
            self.move(dialog_geometry.topLeft())
