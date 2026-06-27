"""Data Engine — application layer.

Use cases that orchestrate the data engine's core logic:
    - SubscribeToFeed       — start streaming ticks for a set of symbols
    - FetchHistoricalBars   — backfill OHLCV from Fyers history API
    - SnapshotOptionsChain  — fetch and cache a full options chain
    - RefreshInstrumentMaster — reload the NSE/BSE instrument list
"""
