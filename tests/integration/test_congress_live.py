"""Integration test — Quiver Quant demo key (no registration needed)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.ingestion.congress import fetch_transactions, get_recent_trades, normalize

pytestmark = pytest.mark.integration


class TestFetchTransactions:
    def test_returns_list(self):
        data = fetch_transactions(verbose=False)
        assert isinstance(data, list)

    def test_nonempty(self):
        data = fetch_transactions(verbose=False)
        assert len(data) > 0

    def test_each_row_has_ticker(self):
        data = fetch_transactions(verbose=False)
        for row in data[:20]:
            assert "Ticker" in row or "ticker" in row

    def test_normalize_roundtrip(self):
        data = fetch_transactions(verbose=False)
        row = data[0]
        out = normalize(row)
        assert "ticker" in out
        assert "trade_type" in out
        assert out["trade_type"] in ("purchase", "sale", "sale_full", "unknown")


class TestGetRecentTrades:
    def test_returns_trades_within_window(self):
        trades = get_recent_trades(days=180)
        assert isinstance(trades, list)
        assert len(trades) > 0

    def test_all_have_tickers(self):
        trades = get_recent_trades(days=180, tickers_only=True)
        for t in trades:
            assert t["ticker"] != ""
