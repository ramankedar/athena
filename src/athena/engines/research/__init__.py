"""Research Engine — backtesting, signal development, and performance analytics.

Responsibilities:
    - Provide an event-driven backtesting framework using the same domain
      event types as the live trading system (no separate research models)
    - Host the signal handler contract that both backtest and live modes share
    - Compute performance analytics (Sharpe, Sortino, max drawdown, etc.)
    - Render tear sheets for strategy evaluation
    - Expose a clean Python API usable from Jupyter notebooks without modification

Key design constraint:
    The backtesting framework replays TickReceived and OHLCVBarClosed events
    from the historical store. Signal handlers written for backtest are
    wire-compatible with the live Trading Engine — changing the event source
    is the only difference between backtest and live execution.
"""
