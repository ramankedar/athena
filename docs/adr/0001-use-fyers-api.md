# ADR-0001: Use Fyers API as the Primary Broker Integration

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Platform Engineering

---

## Context

Athena requires a programmatic interface to an Indian broker for two purposes:
1. Real-time market data (tick-level) for NIFTY, BANKNIFTY, SENSEX, BANKEX
2. Order management (submit, cancel, query) for NSE/BSE derivative instruments

The broker API must:
- Provide a WebSocket feed for real-time tick data
- Expose a REST API for order submission with sub-second latency
- Support F&O instruments (options chains, futures)
- Be SEBI-regulated
- Have a documented, stable API with SDK support

Candidates evaluated: Fyers, Zerodha (Kite Connect), Upstox, Angel Broking (Smart API).

## Decision

Use **Fyers API** as the sole broker integration at launch.

Rationale:
- WebSocket feed supports full order book depth and tick data simultaneously
- REST API is well-documented with Python examples and maintained SDK
- Historical data API covers the full required period for backtesting
- Options chain API returns Greeks (Delta, Gamma, Theta, Vega) natively
- Paper trading environment available for development and staging

## Consequences

**Positive:**
- Single integration to build and maintain at launch
- Well-understood API surface with active developer community
- Paper trading reduces risk during development

**Negative / Risks:**
- Single-broker dependency creates concentration risk (API outages affect entire platform)
- Fyers-specific quirks (lot size encoding, symbol format) will leak into adapters and must be contained in `athena.engines.data.infrastructure` and `athena.engines.trading.infrastructure`

**Mitigation:**
- The `BrokerPort` and `MarketDataFeedPort` protocols in `athena.core.ports` are broker-agnostic
- Adding Zerodha or another broker requires only implementing those protocols — no domain changes
- See ADR-0003 for how hexagonal architecture enforces this isolation
