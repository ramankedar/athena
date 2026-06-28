"""Asset classification enumerations.

Defines the complete taxonomy of asset classes, instrument types, exchange
segments, and instrument lifecycle states used throughout the platform.

The classification hierarchy:
    ``AssetClass``        — broad category (equity, derivative, commodity, etc.)
    ``InstrumentType``    — specific type within the asset class
    ``ExchangeSegment``   — exchange trading segment (NSE_FO, BSE_EQ, etc.)
    ``InstrumentStatus``  — lifecycle state (active, expired, delisted, etc.)
    ``OptionType``        — call or put
    ``OptionStyle``       — exercise style (European, American)
    ``SettlementType``    — how the contract settles (cash, physical)
    ``MarketTier``        — listing tier on an exchange (main board, SME)

Design note on ``ExchangeSegment``:
    Segments are exchange-specific. ``ExchangeId("NSE")`` identifies the
    exchange; ``ExchangeSegment.NSE_FO`` identifies the trading segment within
    that exchange. An instrument on ``NSE_FO`` has a different tick size and
    lot size regime than the same underlying on ``NSE_EQ``.
"""

from __future__ import annotations

from enum import StrEnum


class AssetClass(StrEnum):
    """Broad classification of a financial asset.

    Attributes:
        EQUITY:       Common and preferred stocks, REITs.
        INDEX:        Market indices (non-tradable but can be underlying).
        DERIVATIVE:   Futures and options contracts.
        ETF:          Exchange-traded funds and ETNs.
        CURRENCY:     FX spot and derivatives.
        COMMODITY:    Physical commodities and commodity derivatives.
        FIXED_INCOME: Bonds and other debt instruments (planned).
    """

    EQUITY = "equity"
    INDEX = "index"
    DERIVATIVE = "derivative"
    ETF = "etf"
    CURRENCY = "currency"
    COMMODITY = "commodity"
    FIXED_INCOME = "fixed_income"


class InstrumentType(StrEnum):
    """Specific instrument type within an asset class.

    Each ``InstrumentType`` is associated with exactly one ``AssetClass``:

    EQUITY asset class:
        COMMON_STOCK, PREFERRED_STOCK

    INDEX asset class:
        BROAD_MARKET_INDEX, SECTOR_INDEX, STRATEGY_INDEX, THEMATIC_INDEX

    DERIVATIVE asset class:
        FUTURES, CALL_OPTION, PUT_OPTION

    ETF asset class:
        EQUITY_ETF, DEBT_ETF, GOLD_ETF, COMMODITY_ETF, INTERNATIONAL_ETF

    CURRENCY asset class:
        FX_SPOT, FX_FUTURES, FX_OPTIONS

    COMMODITY asset class:
        COMMODITY_FUTURES, COMMODITY_SPOT, COMMODITY_OPTIONS

    FIXED_INCOME asset class:
        GOVERNMENT_BOND, CORPORATE_BOND, T_BILL (planned)
    """

    # Equity
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"

    # Index
    BROAD_MARKET_INDEX = "broad_market_index"
    SECTOR_INDEX = "sector_index"
    STRATEGY_INDEX = "strategy_index"
    THEMATIC_INDEX = "thematic_index"

    # Derivatives
    FUTURES = "futures"
    CALL_OPTION = "call_option"
    PUT_OPTION = "put_option"

    # ETF
    EQUITY_ETF = "equity_etf"
    DEBT_ETF = "debt_etf"
    GOLD_ETF = "gold_etf"
    COMMODITY_ETF = "commodity_etf"
    INTERNATIONAL_ETF = "international_etf"

    # Currency
    FX_SPOT = "fx_spot"
    FX_FUTURES = "fx_futures"
    FX_OPTIONS = "fx_options"

    # Commodity
    COMMODITY_FUTURES = "commodity_futures"
    COMMODITY_SPOT = "commodity_spot"
    COMMODITY_OPTIONS = "commodity_options"

    # Fixed Income (planned)
    GOVERNMENT_BOND = "government_bond"
    CORPORATE_BOND = "corporate_bond"
    T_BILL = "t_bill"


class ExchangeSegment(StrEnum):
    """Exchange trading segment.

    Segments partition an exchange's instruments by asset class, risk profile,
    and regulatory treatment. Each segment has its own margin requirements,
    circuit breakers, and settlement cycles.

    Indian market segments:
        NSE_EQ:  NSE Cash Equity (T+1 settlement)
        NSE_FO:  NSE Futures & Options (daily MTM, weekly/monthly expiry)
        NSE_CDS: NSE Currency Derivatives (USD/INR, EUR/INR pairs)
        NSE_CD:  NSE Currency (same as CDS in common usage)
        NSE_SME: NSE SME Emerge platform
        BSE_EQ:  BSE Cash Equity (T+1 settlement)
        BSE_FO:  BSE Futures & Options (SENSEX, BANKEX derivatives)
        BSE_SME: BSE SME platform
        MCX_FO:  MCX Commodity Derivatives (gold, silver, crude oil, etc.)

    International segments (planned):
        NYSE_EQ: New York Stock Exchange equity
        NASDAQ_EQ: NASDAQ equity
    """

    # NSE Segments
    NSE_EQ = "NSE_EQ"
    NSE_FO = "NSE_FO"
    NSE_CDS = "NSE_CDS"
    NSE_CD = "NSE_CD"
    NSE_SME = "NSE_SME"

    # BSE Segments
    BSE_EQ = "BSE_EQ"
    BSE_FO = "BSE_FO"
    BSE_SME = "BSE_SME"

    # MCX Segments
    MCX_FO = "MCX_FO"

    # International (planned)
    NYSE_EQ = "NYSE_EQ"
    NASDAQ_EQ = "NASDAQ_EQ"

    @property
    def exchange_code(self) -> str:
        """Extract the exchange code from the segment identifier.

        Returns:
            The exchange code prefix (e.g. ``"NSE"`` for ``NSE_FO``).
        """
        return self.value.split("_")[0]


class InstrumentStatus(StrEnum):
    """Lifecycle state of a listed instrument.

    Attributes:
        ACTIVE:       Instrument is actively trading.
        SUSPENDED:    Trading temporarily halted (circuit breaker, regulatory action).
        EXPIRED:      Derivative contract has reached its expiry date.
        DELISTED:     Instrument has been removed from the exchange.
        PRE_LISTING:  Approved for listing but not yet trading (IPO period).
    """

    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    DELISTED = "delisted"
    PRE_LISTING = "pre_listing"

    @property
    def is_tradable(self) -> bool:
        """Return ``True`` when the instrument can accept new orders.

        Returns:
            ``True`` for ``ACTIVE`` only; ``False`` for all other states.
        """
        return self == InstrumentStatus.ACTIVE


class OptionType(StrEnum):
    """Whether an option contract grants the right to buy or sell.

    Attributes:
        CALL: The holder has the right to BUY the underlying at the strike price.
        PUT:  The holder has the right to SELL the underlying at the strike price.
    """

    CALL = "CE"  # NSE convention: CE = Call European
    PUT = "PE"  # NSE convention: PE = Put European


class OptionStyle(StrEnum):
    """Option exercise style — when the holder may exercise.

    Attributes:
        EUROPEAN: Can only be exercised at expiry. Most NSE index options.
        AMERICAN: Can be exercised at any time before expiry. Most stock options.
        ASIAN:    Payoff based on average price over a period (planned).
    """

    EUROPEAN = "european"
    AMERICAN = "american"
    ASIAN = "asian"


class SettlementType(StrEnum):
    """How a derivative contract settles at expiry.

    Attributes:
        CASH:     Net cash difference between strike and spot is paid/received.
            Most index options and futures on NSE settle in cash.
        PHYSICAL: Delivery of the underlying asset. Commodity contracts, some
            stock futures.
        BOTH:     Either cash or physical, at the holder's election.
    """

    CASH = "cash"
    PHYSICAL = "physical"
    BOTH = "both"


class MarketTier(StrEnum):
    """Listing tier or board within an exchange.

    Attributes:
        MAIN_BOARD:    Standard listing on the main exchange board.
        SME:           Small and Medium Enterprise segment (BSE SME / NSE Emerge).
        INSTITUTIONAL: Reserved for institutional participants only.
    """

    MAIN_BOARD = "main_board"
    SME = "sme"
    INSTITUTIONAL = "institutional"
