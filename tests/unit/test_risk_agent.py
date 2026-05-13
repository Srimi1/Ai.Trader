"""Unit tests for risk guardrails."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.agents.risk_agent import filter_trades, position_size, _disclosure_lag, MAX_POSITION_PCT, MIN_SIGNAL_SCORE
from tests.fixtures.sample_trades import make_normalized_trade


class TestDisclosureLag:
    def test_normal_lag(self):
        tx = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        disc = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        trade = {"transaction_date": tx, "disclosure_date": disc}
        assert _disclosure_lag(trade) == 3

    def test_same_day_zero(self):
        d = datetime.now().strftime("%Y-%m-%d")
        trade = {"transaction_date": d, "disclosure_date": d}
        assert _disclosure_lag(trade) == 0

    def test_bad_date_returns_zero(self):
        trade = {"transaction_date": "bad", "disclosure_date": "bad"}
        assert _disclosure_lag(trade) == 0

    def test_missing_disclosure_uses_tx(self):
        d = datetime.now().strftime("%Y-%m-%d")
        trade = {"transaction_date": d}
        assert _disclosure_lag(trade) == 0


class TestFilterTrades:
    def test_good_trade_approved(self):
        trade = make_normalized_trade(days_ago=5, adjusted_score=1.5)
        approved, rejected = filter_trades([trade])
        assert len(approved) == 1
        assert len(rejected) == 0

    def test_low_score_rejected(self):
        trade = make_normalized_trade(days_ago=5, score=0.1, adjusted_score=0.1)
        _, rejected = filter_trades([trade])
        assert len(rejected) == 1
        assert any("score" in r for r in rejected[0]["rejected_reasons"])

    def test_high_disclosure_lag_rejected(self):
        tx = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        disc = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        trade = make_normalized_trade(days_ago=90, adjusted_score=2.0)
        trade["transaction_date"] = tx
        trade["disclosure_date"] = disc
        _, rejected = filter_trades([trade])
        assert len(rejected) == 1
        assert any("lag" in r for r in rejected[0]["rejected_reasons"])

    def test_no_ticker_rejected(self):
        trade = make_normalized_trade(adjusted_score=2.0)
        trade["ticker"] = ""
        _, rejected = filter_trades([trade])
        assert len(rejected) == 1
        assert any("ticker" in r for r in rejected[0]["rejected_reasons"])

    def test_empty_list(self):
        approved, rejected = filter_trades([])
        assert approved == [] and rejected == []

    def test_multiple_rejection_reasons(self):
        tx = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        disc = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")
        trade = make_normalized_trade(days_ago=90, score=0.1, adjusted_score=0.1)
        trade["transaction_date"] = tx
        trade["disclosure_date"] = disc
        _, rejected = filter_trades([trade])
        assert len(rejected[0]["rejected_reasons"]) >= 2


class TestPositionSize:
    def test_min_score_gives_small_size(self):
        size = position_size(MIN_SIGNAL_SCORE)
        assert 0 < size <= MAX_POSITION_PCT

    def test_large_score_capped_at_max(self):
        size = position_size(100.0)
        assert size == MAX_POSITION_PCT

    def test_zero_score_gives_zero(self):
        assert position_size(0.0) == 0.0

    def test_proportional_scaling(self):
        size_low = position_size(0.5)
        size_high = position_size(2.0)
        assert size_high > size_low
