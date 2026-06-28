"""Athena Market Data Domain — Sprint 6.

Represents historical and live market data independently of any vendor or
storage backend. This package contains only domain models, typed value objects,
and Protocol interfaces — no HTTP clients, WebSocket connections, or databases.

Supported data types:
    OHLCV bars    — aggregated candlestick data with any timeframe
    Ticks         — raw market tick events (trades, bid/ask updates)
    Quotes        — best bid/ask snapshots
    Trades        — individual executed transactions
    Order books   — multi-level depth snapshots
    Corporate actions — dividends, splits, bonuses, etc.
    Adjustments   — price/volume adjustment factors

Public API::

    from athena.market_data import (
        # Enumerations
        Timeframe, TradeSide, TickType, BarState, AdjustmentMethodology,

        # Utilities
        timeframe_seconds, is_intraday,

        # Metadata
        DataProvenance, SymbolMapping,

        # Quality
        QualityFlag, DataQuality,

        # OHLCV
        OHLCVBar, OHLCVSeries, GapInfo,

        # Tick data
        MarketTick,

        # Quotes
        Quote,

        # Trades
        Trade,

        # Order book
        OrderBookLevel, OrderBookSide, OrderBookSnapshot,

        # Corporate actions
        CorporateActionType, CorporateAction,

        # Adjustments
        AdjustmentFactor, AdjustedPrice,
        apply_adjustment, cumulative_price_factor,

        # Interfaces
        HistoricalDataProviderProtocol, LiveDataProviderProtocol,
        CorporateActionProviderProtocol, MarketDataRepositoryProtocol,

        # Validation
        ValidationResult,
        validate_ohlcv_bar, validate_ohlcv_series, validate_tick,
        validate_quote, validate_trade, validate_order_book,
        validate_adjustment_factor,

        # Exceptions
        MarketDataError, InvalidBarError, InvalidTickError,
        InvalidQuoteError, InvalidTradeError, InvalidOrderBookError,
        InvalidSeriesError, DataGapError, InvalidAdjustmentError,
        ProviderError,
    )
"""

from athena.market_data.adjustments import (
    AdjustedPrice,
    AdjustmentFactor,
    apply_adjustment,
    cumulative_price_factor,
)
from athena.market_data.corporate_actions import CorporateAction, CorporateActionType
from athena.market_data.exceptions import (
    DataGapError,
    InvalidAdjustmentError,
    InvalidBarError,
    InvalidOrderBookError,
    InvalidQuoteError,
    InvalidSeriesError,
    InvalidTickError,
    InvalidTradeError,
    MarketDataError,
    ProviderError,
)
from athena.market_data.interfaces import (
    CorporateActionProviderProtocol,
    HistoricalDataProviderProtocol,
    LiveDataProviderProtocol,
    MarketDataRepositoryProtocol,
)
from athena.market_data.metadata import DataProvenance, SymbolMapping
from athena.market_data.models import (
    AdjustmentMethodology,
    BarState,
    TickType,
    Timeframe,
    TradeSide,
    is_intraday,
    timeframe_seconds,
)
from athena.market_data.ohlcv import GapInfo, OHLCVBar, OHLCVSeries
from athena.market_data.orderbook import OrderBookLevel, OrderBookSide, OrderBookSnapshot
from athena.market_data.quality import DataQuality, QualityFlag
from athena.market_data.quotes import Quote
from athena.market_data.ticks import MarketTick
from athena.market_data.trades import Trade
from athena.market_data.validation import (
    ValidationResult,
    validate_adjustment_factor,
    validate_ohlcv_bar,
    validate_ohlcv_series,
    validate_order_book,
    validate_quote,
    validate_tick,
    validate_trade,
)

__all__ = [
    "AdjustedPrice",
    "AdjustmentFactor",
    "AdjustmentMethodology",
    "BarState",
    "CorporateAction",
    "CorporateActionProviderProtocol",
    "CorporateActionType",
    "DataGapError",
    "DataProvenance",
    "DataQuality",
    "GapInfo",
    "HistoricalDataProviderProtocol",
    "InvalidAdjustmentError",
    "InvalidBarError",
    "InvalidOrderBookError",
    "InvalidQuoteError",
    "InvalidSeriesError",
    "InvalidTickError",
    "InvalidTradeError",
    "LiveDataProviderProtocol",
    "MarketDataError",
    "MarketDataRepositoryProtocol",
    "MarketTick",
    "OHLCVBar",
    "OHLCVSeries",
    "OrderBookLevel",
    "OrderBookSide",
    "OrderBookSnapshot",
    "ProviderError",
    "QualityFlag",
    "Quote",
    "SymbolMapping",
    "TickType",
    "Timeframe",
    "Trade",
    "TradeSide",
    "ValidationResult",
    "apply_adjustment",
    "cumulative_price_factor",
    "is_intraday",
    "timeframe_seconds",
    "validate_adjustment_factor",
    "validate_ohlcv_bar",
    "validate_ohlcv_series",
    "validate_order_book",
    "validate_quote",
    "validate_tick",
    "validate_trade",
]
