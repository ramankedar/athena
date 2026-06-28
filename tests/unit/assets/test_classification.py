"""Unit tests for asset classification enumerations."""

from __future__ import annotations

from athena.assets.classification import (
    AssetClass,
    ExchangeSegment,
    InstrumentStatus,
    InstrumentType,
    MarketTier,
    OptionStyle,
    OptionType,
    SettlementType,
)


class TestAssetClass:
    def test_values(self) -> None:
        assert AssetClass.EQUITY == "equity"
        assert AssetClass.INDEX == "index"
        assert AssetClass.DERIVATIVE == "derivative"
        assert AssetClass.ETF == "etf"
        assert AssetClass.CURRENCY == "currency"
        assert AssetClass.COMMODITY == "commodity"
        assert AssetClass.FIXED_INCOME == "fixed_income"

    def test_is_str(self) -> None:
        assert isinstance(AssetClass.EQUITY, str)

    def test_all_members_count(self) -> None:
        assert len(AssetClass) == 7


class TestInstrumentType:
    def test_equity_types(self) -> None:
        assert InstrumentType.COMMON_STOCK == "common_stock"
        assert InstrumentType.PREFERRED_STOCK == "preferred_stock"

    def test_index_types(self) -> None:
        assert InstrumentType.BROAD_MARKET_INDEX == "broad_market_index"
        assert InstrumentType.SECTOR_INDEX == "sector_index"
        assert InstrumentType.STRATEGY_INDEX == "strategy_index"
        assert InstrumentType.THEMATIC_INDEX == "thematic_index"

    def test_derivative_types(self) -> None:
        assert InstrumentType.FUTURES == "futures"
        assert InstrumentType.CALL_OPTION == "call_option"
        assert InstrumentType.PUT_OPTION == "put_option"

    def test_etf_types(self) -> None:
        assert InstrumentType.EQUITY_ETF == "equity_etf"
        assert InstrumentType.DEBT_ETF == "debt_etf"
        assert InstrumentType.GOLD_ETF == "gold_etf"

    def test_currency_types(self) -> None:
        assert InstrumentType.FX_SPOT == "fx_spot"
        assert InstrumentType.FX_FUTURES == "fx_futures"

    def test_commodity_types(self) -> None:
        assert InstrumentType.COMMODITY_FUTURES == "commodity_futures"
        assert InstrumentType.COMMODITY_SPOT == "commodity_spot"

    def test_is_str(self) -> None:
        assert isinstance(InstrumentType.FUTURES, str)


class TestExchangeSegment:
    def test_nse_segments(self) -> None:
        assert ExchangeSegment.NSE_EQ == "NSE_EQ"
        assert ExchangeSegment.NSE_FO == "NSE_FO"
        assert ExchangeSegment.NSE_CDS == "NSE_CDS"
        assert ExchangeSegment.NSE_SME == "NSE_SME"

    def test_bse_segments(self) -> None:
        assert ExchangeSegment.BSE_EQ == "BSE_EQ"
        assert ExchangeSegment.BSE_FO == "BSE_FO"

    def test_mcx_segments(self) -> None:
        assert ExchangeSegment.MCX_FO == "MCX_FO"

    def test_exchange_code_property_nse(self) -> None:
        assert ExchangeSegment.NSE_FO.exchange_code == "NSE"

    def test_exchange_code_property_bse(self) -> None:
        assert ExchangeSegment.BSE_EQ.exchange_code == "BSE"

    def test_exchange_code_property_mcx(self) -> None:
        assert ExchangeSegment.MCX_FO.exchange_code == "MCX"


class TestInstrumentStatus:
    def test_values(self) -> None:
        assert InstrumentStatus.ACTIVE == "active"
        assert InstrumentStatus.SUSPENDED == "suspended"
        assert InstrumentStatus.EXPIRED == "expired"
        assert InstrumentStatus.DELISTED == "delisted"
        assert InstrumentStatus.PRE_LISTING == "pre_listing"

    def test_is_tradable_active(self) -> None:
        assert InstrumentStatus.ACTIVE.is_tradable is True

    def test_is_tradable_other_states(self) -> None:
        assert InstrumentStatus.SUSPENDED.is_tradable is False
        assert InstrumentStatus.EXPIRED.is_tradable is False
        assert InstrumentStatus.DELISTED.is_tradable is False
        assert InstrumentStatus.PRE_LISTING.is_tradable is False


class TestOptionType:
    def test_call_value(self) -> None:
        assert OptionType.CALL == "CE"

    def test_put_value(self) -> None:
        assert OptionType.PUT == "PE"

    def test_is_str(self) -> None:
        assert isinstance(OptionType.CALL, str)


class TestOptionStyle:
    def test_values(self) -> None:
        assert OptionStyle.EUROPEAN == "european"
        assert OptionStyle.AMERICAN == "american"
        assert OptionStyle.ASIAN == "asian"


class TestSettlementType:
    def test_values(self) -> None:
        assert SettlementType.CASH == "cash"
        assert SettlementType.PHYSICAL == "physical"
        assert SettlementType.BOTH == "both"


class TestMarketTier:
    def test_values(self) -> None:
        assert MarketTier.MAIN_BOARD == "main_board"
        assert MarketTier.SME == "sme"
        assert MarketTier.INSTITUTIONAL == "institutional"
