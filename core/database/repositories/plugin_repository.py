"""
Plugin state repository for managing plugin enable/disable state and configuration.

Handles database operations for plugin persistence including
enabled state and JSON configuration storage.
"""
from __future__ import annotations

from typing import Optional

from core.database.repositories.base_repository import BaseRepository


class PluginRepository(BaseRepository):
    """Repository for plugin state database operations."""

    def set_plugin_enabled(self, plugin_name: str, enabled: bool) -> None:
        """
        Enable or disable a plugin.

        Args:
            plugin_name: Unique identifier for the plugin
            enabled: Whether the plugin should be enabled
        """
        self._execute(
            """
            INSERT INTO plugin_state (plugin_name, enabled)
            VALUES (?, ?)
            ON CONFLICT(plugin_name)
            DO UPDATE SET enabled = ?
            """,
            (plugin_name, enabled, enabled),
        )

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Check if a plugin is enabled.

        Args:
            plugin_name: Unique identifier for the plugin

        Returns:
            True if plugin is enabled, False otherwise (including if not found)
        """
        row = self._execute_fetchone(
            "SELECT enabled FROM plugin_state WHERE plugin_name = ?",
            (plugin_name,),
        )
        return bool(row[0]) if row else False

    def set_plugin_config(self, plugin_name: str, config_json: str) -> None:
        """
        Store plugin-specific JSON configuration.

        Args:
            plugin_name: Unique identifier for the plugin
            config_json: JSON string containing plugin configuration
        """
        self._execute(
            """
            INSERT INTO plugin_state (plugin_name, config_json)
            VALUES (?, ?)
            ON CONFLICT(plugin_name)
            DO UPDATE SET config_json = ?
            """,
            (plugin_name, config_json, config_json),
        )

    def get_plugin_config(self, plugin_name: str) -> Optional[str]:
        """
        Return stored plugin configuration JSON.

        Args:
            plugin_name: Unique identifier for the plugin

        Returns:
            JSON configuration string, or None if not found
        """
        row = self._execute_fetchone(
            "SELECT config_json FROM plugin_state WHERE plugin_name = ?",
            (plugin_name,),
        )
        return row[0] if row else None
