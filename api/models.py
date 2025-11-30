"""
api.models - Pydantic models for API request/response schemas.

These models provide type-safe data validation for all API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# Enums
# ==============================================================================


class GameVersion(str, Enum):
    """Supported game versions."""

    POE1 = "poe1"
    POE2 = "poe2"


class ItemRarity(str, Enum):
    """Item rarity types."""

    NORMAL = "normal"
    MAGIC = "magic"
    RARE = "rare"
    UNIQUE = "unique"
    CURRENCY = "currency"
    GEM = "gem"
    DIVINATION = "divination"


# ==============================================================================
# Price Check Models
# ==============================================================================


class PriceCheckRequest(BaseModel):
    """Request model for price checking an item."""

    item_text: str = Field(
        ...,
        description="Raw item text from clipboard (Ctrl+C in game)",
        min_length=1,
        examples=[
            "Rarity: Unique\nHeadhunter\nLeather Belt\n--------\nRequirements:\nLevel: 40\n--------\nWhen you Kill a Rare Monster, you gain its Modifiers for 20 seconds"
        ],
    )
    game_version: GameVersion = Field(
        default=GameVersion.POE1, description="Game version (poe1 or poe2)"
    )
    league: Optional[str] = Field(
        default=None,
        description="League name. If not specified, uses configured default.",
        examples=["Standard", "Hardcore", "Settlers"],
    )


class PriceSource(BaseModel):
    """Price data from a single source."""

    source: str = Field(..., description="Price source name", examples=["poe.ninja"])
    chaos_value: Optional[float] = Field(
        None, description="Price in chaos orbs", ge=0, examples=[15000.0]
    )
    divine_value: Optional[float] = Field(
        None, description="Price in divine orbs", ge=0, examples=[85.5]
    )
    listing_count: Optional[int] = Field(
        None, description="Number of listings found", ge=0, examples=[42]
    )
    confidence: Optional[float] = Field(
        None, description="Confidence score (0-1)", ge=0, le=1, examples=[0.95]
    )


class ParsedItemInfo(BaseModel):
    """Parsed item information."""

    name: str = Field(..., description="Item name", examples=["Headhunter"])
    base_type: Optional[str] = Field(
        None, description="Base item type", examples=["Leather Belt"]
    )
    rarity: Optional[str] = Field(
        None, description="Item rarity", examples=["unique"]
    )
    item_level: Optional[int] = Field(
        None, description="Item level", ge=1, examples=[86]
    )
    mods: list[str] = Field(
        default_factory=list, description="List of item modifiers"
    )
    sockets: Optional[str] = Field(
        None, description="Socket configuration", examples=["R-R-R-R-B-G"]
    )
    corrupted: bool = Field(default=False, description="Whether item is corrupted")
    influences: list[str] = Field(
        default_factory=list,
        description="Item influences",
        examples=[["shaper", "elder"]],
    )


class PriceCheckResponse(BaseModel):
    """Response model for price check results."""

    success: bool = Field(..., description="Whether price check succeeded")
    item: Optional[ParsedItemInfo] = Field(
        None, description="Parsed item information"
    )
    prices: list[PriceSource] = Field(
        default_factory=list, description="Price data from various sources"
    )
    best_price: Optional[float] = Field(
        None, description="Best estimated price in chaos", examples=[15000.0]
    )
    explanation: Optional[str] = Field(
        None, description="Human-readable price explanation"
    )
    error: Optional[str] = Field(None, description="Error message if check failed")
    checked_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of price check"
    )


# ==============================================================================
# Item History Models
# ==============================================================================


class CheckedItemResponse(BaseModel):
    """Response model for a checked item from history."""

    id: int = Field(..., description="Database ID")
    game_version: str = Field(..., description="Game version")
    league: str = Field(..., description="League name")
    item_name: str = Field(..., description="Item name")
    chaos_value: Optional[float] = Field(None, description="Price in chaos")
    divine_value: Optional[float] = Field(None, description="Price in divine orbs")
    rarity: Optional[str] = Field(None, description="Item rarity")
    checked_at: datetime = Field(..., description="When item was checked")


class ItemsListResponse(BaseModel):
    """Response model for list of checked items."""

    items: list[CheckedItemResponse] = Field(..., description="List of checked items")
    total: int = Field(..., description="Total number of items matching filters")
    limit: int = Field(..., description="Maximum items returned")
    offset: int = Field(..., description="Offset for pagination")


# ==============================================================================
# Sales Models
# ==============================================================================


class SaleCreate(BaseModel):
    """Request model for creating a new sale listing."""

    item_name: str = Field(..., description="Name of item being sold", min_length=1)
    listed_price_chaos: float = Field(
        ..., description="Listed price in chaos", gt=0, examples=[100.0]
    )
    notes: Optional[str] = Field(None, description="Optional notes about the sale")


class SaleUpdate(BaseModel):
    """Request model for updating a sale (marking as sold)."""

    actual_price_chaos: Optional[float] = Field(
        None, description="Actual sale price in chaos", gt=0
    )
    notes: Optional[str] = Field(None, description="Updated notes")


class SaleResponse(BaseModel):
    """Response model for a sale record."""

    id: int = Field(..., description="Sale ID")
    item_name: str = Field(..., description="Item name")
    listed_price_chaos: float = Field(..., description="Listed price")
    actual_price_chaos: Optional[float] = Field(None, description="Actual sale price")
    listed_at: datetime = Field(..., description="When item was listed")
    sold_at: Optional[datetime] = Field(None, description="When item was sold")
    time_to_sale_hours: Optional[float] = Field(
        None, description="Hours from listing to sale"
    )
    notes: Optional[str] = Field(None, description="Notes")


class SalesListResponse(BaseModel):
    """Response model for list of sales."""

    sales: list[SaleResponse] = Field(..., description="List of sales")
    total: int = Field(..., description="Total sales matching filters")
    limit: int = Field(..., description="Maximum items returned")
    offset: int = Field(..., description="Offset for pagination")


# ==============================================================================
# Statistics Models
# ==============================================================================


class DailySummary(BaseModel):
    """Daily sales summary."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    total_sales: int = Field(..., description="Number of sales")
    total_chaos: float = Field(..., description="Total chaos earned")
    avg_time_to_sale: Optional[float] = Field(
        None, description="Average hours to sell"
    )


class StatsResponse(BaseModel):
    """Response model for aggregated statistics."""

    period_days: int = Field(..., description="Statistics period in days")
    total_items_checked: int = Field(..., description="Total items price checked")
    total_sales: int = Field(..., description="Total completed sales")
    total_chaos_earned: float = Field(..., description="Total chaos from sales")
    total_divine_equivalent: Optional[float] = Field(
        None, description="Total in divine orbs"
    )
    avg_price_per_sale: Optional[float] = Field(
        None, description="Average sale price"
    )
    avg_time_to_sale_hours: Optional[float] = Field(
        None, description="Average time to sell"
    )
    daily_summary: list[DailySummary] = Field(
        default_factory=list, description="Daily breakdown"
    )
    top_items: list[dict[str, Any]] = Field(
        default_factory=list, description="Most valuable items sold"
    )


# ==============================================================================
# Health & Status Models
# ==============================================================================


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Service status", examples=["healthy"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    database: str = Field(
        ..., description="Database status", examples=["connected"]
    )
    services: dict[str, str] = Field(
        default_factory=dict, description="Status of individual services"
    )


class ConfigResponse(BaseModel):
    """Response model for configuration info."""

    game_version: str = Field(..., description="Current game version")
    league: str = Field(..., description="Current league")
    auto_detect_league: bool = Field(..., description="Auto-detect league setting")
    cache_ttl_seconds: int = Field(..., description="Cache TTL in seconds")
