"""Athena — AI-powered quantitative research and automated trading platform.

Indian derivative markets (NIFTY, BANKNIFTY, SENSEX, BANKEX) via Fyers API.

Five-engine architecture:
    athena.engines.data        — market data ingestion and storage
    athena.engines.research    — backtesting and signal development
    athena.engines.intelligence — ML pipeline (planned)
    athena.engines.trading     — order management and risk
    athena.engines.governance  — audit trail and compliance
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("athena")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
