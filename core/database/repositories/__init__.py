"""
Database repositories package.

Provides domain-specific repository classes for database operations.
Each repository handles a specific domain (sales, prices, etc.) and
inherits from BaseRepository for thread-safe execution.

Public API:
- BaseRepository: Base class for all repositories
- SalesRepository: Sales tracking operations
- PriceRepository: Price history and checks
- CheckedItemsRepository: Checked item tracking
- PluginRepository: Plugin state management
- CurrencyRepository: Currency rate tracking
- UpgradeAdviceRepository: Upgrade advice cache and history
- VerdictRepository: Verdict statistics
- PriceAlertRepository: Price alert monitoring
- StatsRepository: Aggregate statistics and maintenance
"""
from core.database.repositories.base_repository import BaseRepository
from core.database.repositories.checked_items_repository import CheckedItemsRepository
from core.database.repositories.currency_repository import CurrencyRepository
from core.database.repositories.plugin_repository import PluginRepository
from core.database.repositories.price_alert_repository import PriceAlertRepository
from core.database.repositories.price_repository import PriceRepository
from core.database.repositories.sales_repository import SalesRepository
from core.database.repositories.stats_repository import StatsRepository
from core.database.repositories.upgrade_advice_repository import UpgradeAdviceRepository
from core.database.repositories.verdict_repository import VerdictRepository

__all__ = [
    "BaseRepository",
    "CheckedItemsRepository",
    "CurrencyRepository",
    "PluginRepository",
    "PriceAlertRepository",
    "PriceRepository",
    "SalesRepository",
    "StatsRepository",
    "UpgradeAdviceRepository",
    "VerdictRepository",
]
