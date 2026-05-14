"""Integration tests for price fetcher — uses yfinance (free, no key)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.ingestion.prices import get_price_history, get_price_on_date, get_return_since


pytestmark = pytest.mark.integration


class TestGetPriceHistory:
    def test_returns_dataframe(self):
        df = get_price_history("SPY", days=10)
        assert isinstance(df, pd.DataFrame)

    def test_has_ohlcv_columns(self):
        df = get_price_history("SPY", days=30)
        assert not df.empty
        assert "close" in df.columns

    def test_nvidia_data(self):
        df = get_price_history("NVDA", days=30)
        assert not df.empty
        assert df["close"].iloc[-1] > 0

    def test_invalid_ticker_returns_empty(self):
        df = get_price_history("ZZZZINVALID999", days=30)
        assert df.empty or len(df) == 0


class TestGetPriceOnDate:
    def test_returns_float(self):
        price = get_price_on_date("SPY", "2024-01-15")
        assert price is not None
        assert isinstance(price, float)
        assert price > 0

    def test_future_date_returns_none(self):
        price = get_price_on_date("SPY", "2099-01-01")
        assert price is None

    def test_weekend_returns_nearest_trading_day(self):
        # 2024-01-13 was a Saturday — should return nearest trading day price
        price = get_price_on_date("SPY", "2024-01-13")
        assert price is not None


class TestGetReturnSince:
    def test_returns_float(self):
        ret = get_return_since("SPY", "2024-01-02", days_held=30)
        assert isinstance(ret, float)

    def test_spy_return_wrapper(self):
        from src.ingestion.prices import get_spy_return
        ret = get_spy_return("2024-01-02", days_held=30)
        assert isinstance(ret, float)
