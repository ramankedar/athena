"""Data Engine — market data ingestion, normalisation, and storage.

Responsibilities:
    - Subscribe to Fyers WebSocket for real-time tick data
    - Normalise raw exchange payloads into Tick domain events
    - Aggregate ticks into OHLCV bars and publish BarClosed events
    - Persist historical OHLCV and tick data in TimescaleDB
    - Serve historical data queries to Research and backtesting
    - Maintain and refresh the instrument master cache
    - Detect data quality issues (gaps, stale feed, outlier prices)
    - Fetch and cache options chain snapshots

This engine is the single source of truth for all market data.
No other engine reads from external market data sources directly.
"""
