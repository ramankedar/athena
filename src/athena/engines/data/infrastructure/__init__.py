"""Data Engine — infrastructure layer.

Concrete adapters that connect the data engine to external systems:
    FyersWebSocketAdapter     — implements MarketDataFeedPort
    FyersHistoricalAdapter    — Fyers REST history API client
    TimescaleHistoricalStore  — implements HistoricalStorePort (TimescaleDB)
    RedisInstrumentCache      — implements InstrumentRepositoryPort (Redis + DB)
"""
