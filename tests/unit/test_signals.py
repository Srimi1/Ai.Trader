"""Unit tests for signal scoring — pure logic, no I/O."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.analysis.signals import (
    _amount_weight,
    _politician_weight,
    _recency_weight,
    _cluster_bonus,
    score_trade,
    score_all,
)
from tests.fixtures.sample_trades import SAMPLE_NORMALIZED_TRADES


class TestAmountWeight:
    def test_high_amount(self):
        assert _amount_weight("$250,001 - $500,000") > _amount_weight("$1,001 - $15,000")

    def test_all_tiers_return_positive(self):
        tiers = [
            "$1,001 - $15,000",
            "$15,001 - $50,000",
            "$50,001 - $100,000",
            "$100,001 - $250,000",
            "$250,001 - $500,000",
            "$500,001 - $1,000,000",
        ]
        for t in tiers:
            assert _amount_weight(t) > 0

    def test_unknown_returns_default(self):
        assert _amount_weight("unknown range") == 0.8


class TestPoliticianWeight:
    def test_known_high_influence_above_1(self):
        w = _politician_weight("Nancy Pelosi")
        assert w > 1.0

    def test_unknown_politician_returns_positive(self):
        w = _politician_weight("John Nobody")
        assert w > 0

    def test_returns_float(self):
        assert isinstance(_politician_weight("Nancy Pelosi"), float)


class TestRecencyWeight:
    def test_recent_trade_higher(self):
        today = datetime.now().strftime("%Y-%m-%d")
        old = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        assert _recency_weight(today) > _recency_weight(old)

    def test_same_day_near_one(self):
        today = datetime.now().strftime("%Y-%m-%d")
        assert _recency_weight(today) > 0.9

    def test_60_days_decayed(self):
        old = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        assert _recency_weight(old) < 0.1

    def test_invalid_date_returns_fallback(self):
        assert _recency_weight("not-a-date") == 0.5


class TestClusterBonus:
    def test_no_cluster_returns_one(self):
        trades = [SAMPLE_NORMALIZED_TRADES[0]]  # single trade
        # different ticker → no cluster
        bonus = _cluster_bonus("ZZZZ", trades)
        assert bonus == 1.0

    def test_multiple_purchases_boost(self):
        today = datetime.now().strftime("%Y-%m-%d")
        trades = [
            {"ticker": "NVDA", "trade_type": "purchase", "transaction_date": today},
            {"ticker": "NVDA", "trade_type": "purchase", "transaction_date": today},
            {"ticker": "NVDA", "trade_type": "purchase", "transaction_date": today},
        ]
        bonus = _cluster_bonus("NVDA", trades)
        assert bonus > 1.0

    def test_sales_dont_count(self):
        today = datetime.now().strftime("%Y-%m-%d")
        trades = [
            {"ticker": "NVDA", "trade_type": "sale", "transaction_date": today},
            {"ticker": "NVDA", "trade_type": "sale", "transaction_date": today},
        ]
        bonus = _cluster_bonus("NVDA", trades)
        assert bonus == 1.0


class TestScoreTrade:
    def test_purchase_positive_score(self):
        trade = SAMPLE_NORMALIZED_TRADES[0]  # purchase
        result = score_trade(trade, SAMPLE_NORMALIZED_TRADES)
        assert result["score"] > 0

    def test_sale_negative_score(self):
        trade = SAMPLE_NORMALIZED_TRADES[1]  # sale
        result = score_trade(trade, SAMPLE_NORMALIZED_TRADES)
        assert result["score"] < 0

    def test_sale_full_negative(self):
        trade = SAMPLE_NORMALIZED_TRADES[4]  # sale_full
        result = score_trade(trade, SAMPLE_NORMALIZED_TRADES)
        assert result["score"] < 0

    def test_output_has_signal_field(self):
        trade = SAMPLE_NORMALIZED_TRADES[0]
        result = score_trade(trade, SAMPLE_NORMALIZED_TRADES)
        assert result["signal"] in ("BUY", "SELL", "NEUTRAL")

    def test_score_components_present(self):
        trade = SAMPLE_NORMALIZED_TRADES[0]
        result = score_trade(trade, SAMPLE_NORMALIZED_TRADES)
        components = result["score_components"]
        assert all(k in components for k in ("politician", "amount", "recency", "cluster"))

    def test_buy_signal_for_high_positive_score(self):
        today = datetime.now().strftime("%Y-%m-%d")
        trade = {
            "representative": "Nancy Pelosi",
            "ticker": "NVDA",
            "trade_type": "purchase",
            "amount_range": "$250,001 - $500,000",
            "transaction_date": today,
            "disclosure_date": today,
        }
        result = score_trade(trade, [trade])
        assert result["signal"] == "BUY"


class TestScoreAll:
    def test_sorted_by_abs_score_desc(self):
        results = score_all(SAMPLE_NORMALIZED_TRADES)
        scores = [abs(r["score"]) for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_skips_empty_ticker(self):
        no_ticker = {**SAMPLE_NORMALIZED_TRADES[0], "ticker": ""}
        results = score_all([no_ticker])
        assert len(results) == 0

    def test_returns_all_valid(self):
        results = score_all(SAMPLE_NORMALIZED_TRADES)
        assert len(results) == len(SAMPLE_NORMALIZED_TRADES)
