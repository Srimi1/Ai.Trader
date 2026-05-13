"""Unit tests for congressional trade ingestion — no network required."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.ingestion.congress import (
    _generate_demo_data,
    normalize,
    get_recent_trades,
    _cache_fresh,
)
from tests.fixtures.sample_trades import SAMPLE_RAW_TRADES


class TestGenerateDemoData:
    def test_returns_list(self):
        data = _generate_demo_data(10)
        assert isinstance(data, list)
        assert len(data) == 10

    def test_required_fields_present(self):
        data = _generate_demo_data(5)
        required = {"Representative", "Ticker", "Transaction", "Range", "TransactionDate", "ReportDate"}
        for row in data:
            assert required.issubset(row.keys()), f"Missing fields in: {row.keys()}"

    def test_deterministic(self):
        a = _generate_demo_data(20)
        b = _generate_demo_data(20)
        assert a == b

    def test_tickers_are_strings(self):
        data = _generate_demo_data(20)
        for row in data:
            assert isinstance(row["Ticker"], str)
            assert len(row["Ticker"]) > 0


class TestNormalize:
    def test_purchase_mapped(self):
        raw = SAMPLE_RAW_TRADES[0]  # Nancy Pelosi NVDA Purchase
        out = normalize(raw)
        assert out["trade_type"] == "purchase"

    def test_sale_mapped(self):
        raw = SAMPLE_RAW_TRADES[1]  # Dan Crenshaw MSFT Sale
        out = normalize(raw)
        assert out["trade_type"] == "sale"

    def test_sale_full_mapped(self):
        raw = SAMPLE_RAW_TRADES[4]  # Michael McCaul AMZN Sale (Full)
        out = normalize(raw)
        assert out["trade_type"] == "sale_full"

    def test_ticker_uppercased(self):
        raw = {**SAMPLE_RAW_TRADES[0], "Ticker": "nvda"}
        out = normalize(raw)
        assert out["ticker"] == "NVDA"

    def test_senate_source(self):
        raw = SAMPLE_RAW_TRADES[2]  # Tommy Tuberville Senate
        out = normalize(raw)
        assert out["source"] == "senate"

    def test_house_source(self):
        raw = SAMPLE_RAW_TRADES[0]  # Nancy Pelosi House
        out = normalize(raw)
        assert out["source"] == "house"

    def test_unknown_transaction_mapped(self):
        raw = {**SAMPLE_RAW_TRADES[0], "Transaction": "Exchange"}
        out = normalize(raw)
        assert out["trade_type"] == "exchange"

    def test_output_schema(self):
        out = normalize(SAMPLE_RAW_TRADES[0])
        keys = {"source", "representative", "ticker", "trade_type", "amount_range",
                "transaction_date", "disclosure_date", "excess_return"}
        assert keys.issubset(out.keys())


class TestGetRecentTrades:
    @patch("src.ingestion.congress.fetch_transactions")
    def test_filters_by_days(self, mock_fetch):
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        recent_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        mock_fetch.return_value = [
            {**SAMPLE_RAW_TRADES[0], "TransactionDate": recent_date},
            {**SAMPLE_RAW_TRADES[1], "TransactionDate": old_date},
        ]
        trades = get_recent_trades(days=90)
        assert all(
            datetime.strptime(t["transaction_date"], "%Y-%m-%d") >= datetime.now() - timedelta(days=90)
            for t in trades
        )

    @patch("src.ingestion.congress.fetch_transactions")
    def test_excludes_empty_tickers(self, mock_fetch):
        noticker = {**SAMPLE_RAW_TRADES[0], "Ticker": ""}
        mock_fetch.return_value = [noticker]
        trades = get_recent_trades(days=90, tickers_only=True)
        assert len(trades) == 0

    @patch("src.ingestion.congress.fetch_transactions")
    def test_sorted_by_date_desc(self, mock_fetch):
        dates = ["2026-01-01", "2026-03-01", "2026-02-01"]
        rows = [{**SAMPLE_RAW_TRADES[0], "TransactionDate": d} for d in dates]
        mock_fetch.return_value = rows
        trades = get_recent_trades(days=9999)
        for i in range(len(trades) - 1):
            assert trades[i]["transaction_date"] >= trades[i + 1]["transaction_date"]

    @patch("src.ingestion.congress.fetch_transactions")
    def test_bad_date_skipped(self, mock_fetch):
        bad = {**SAMPLE_RAW_TRADES[0], "TransactionDate": "not-a-date"}
        mock_fetch.return_value = [bad]
        trades = get_recent_trades(days=90)
        assert len(trades) == 0
