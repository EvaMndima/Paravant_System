"""Data layer module for database models and market data access.

Decision: DEC-2026-02-10-001 - Use python-binance SDK wrapper
Decision: DEC-2026-02-08-002 - SQLAlchemy 2.0 with Mapped[T]

This module provides:
- Database models (Account, Strategy, Order, Position, etc.)
- Market data fetching and validation (OHLCV, symbols)
- Data quality validation (PRD Feature H)
- Symbol management
- Centralized DataStore for all database operations

Example:
    ```python
    from src.data import DataStore, MarketDataService, SymbolManager

    # Initialize services
    store = DataStore()
    market_data = MarketDataService()
    symbol_manager = SymbolManager()

    # Fetch and validate OHLCV data
    series, validation = await market_data.get_ohlcv("BTCUSDT", "1h")

    # Get symbol metadata
    symbol_info = await symbol_manager.get_symbol("BTCUSDT")

    # Persist to database
    store.save_symbol_info(symbol_info)
    ```
"""

# Database models (from Phase 1)
from .models import (
    Base,
    TimestampMixin,
    generate_id,
    Account,
    AccountStatus,
    RiskProfile,
    Strategy,
    StrategyStatus,
    StrategyType,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    PositionSide,
    PositionStatus,
    Trade,
    PnLRecord,
    EquitySnapshot,
    StrategyAssignment,
    AssignmentStatus,
    SystemState,
    AuditLog,
    Signal,
    SignalDirection,
    SymbolInfo,
)

# Database access
from .database import engine, get_db, init_db, reset_db
from .store import DataStore

# Market data (Phase 2)
from .market_data import OHLCV, OHLCVSeries, MarketDataFetcher

# Data validation (Phase 2 - PRD Feature H)
from .validators import (
    DataValidator,
    ValidationResult,
    ACTION_USE,
    ACTION_INTERPOLATE,
    ACTION_REJECT,
    ACTION_PAUSE,
    DATA_QUALITY_THRESHOLDS,
)

# Market data service (Phase 2)
from .service import MarketDataService

# Symbol management (Phase 2)
from .symbol_manager import SymbolManager, CACHE_DURATION_HOURS

__all__ = [
    # =========================================================================
    # DATABASE MODELS (Phase 1)
    # =========================================================================
    # Base
    "Base",
    "TimestampMixin",
    "generate_id",
    # Account
    "Account",
    "AccountStatus",
    "RiskProfile",
    # Strategy
    "Strategy",
    "StrategyStatus",
    "StrategyType",
    # Order
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    # Position
    "Position",
    "PositionSide",
    "PositionStatus",
    # Trade
    "Trade",
    # P&L
    "PnLRecord",
    "EquitySnapshot",
    # Strategy Assignment
    "StrategyAssignment",
    "AssignmentStatus",
    # System
    "SystemState",
    "AuditLog",
    # Signal
    "Signal",
    "SignalDirection",
    # Symbol
    "SymbolInfo",
    # =========================================================================
    # DATABASE ACCESS (Phase 1)
    # =========================================================================
    "engine",
    "get_db",
    "init_db",
    "reset_db",
    "DataStore",
    # =========================================================================
    # MARKET DATA (Phase 2)
    # =========================================================================
    # OHLCV structures
    "OHLCV",
    "OHLCVSeries",
    "MarketDataFetcher",
    # Data validation (PRD Feature H)
    "DataValidator",
    "ValidationResult",
    "ACTION_USE",
    "ACTION_INTERPOLATE",
    "ACTION_REJECT",
    "ACTION_PAUSE",
    "DATA_QUALITY_THRESHOLDS",
    # Market data service
    "MarketDataService",
    # Symbol management
    "SymbolManager",
    "CACHE_DURATION_HOURS",
]
