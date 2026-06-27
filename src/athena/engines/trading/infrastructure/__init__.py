"""Trading Engine — infrastructure layer.

Adapters:
    FyersOrderAdapter       — implements BrokerPort for the Fyers REST API
    FyersWebSocketFillFeed  — listens for order fill events via Fyers WebSocket
    PostgresPositionLedger  — persists and queries position state in TimescaleDB
    RedisIdempotencyCache   — short-lived idempotency key store (TTL: 60s)
    CircuitBreakerStore     — tracks circuit breaker state in Redis
"""
