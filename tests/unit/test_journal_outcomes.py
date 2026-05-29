"""Unit tests for the closed-loop feedback layer (src.portfolio.scorecard).

Signals are logged via Journal, then scored via Scorecard against the same DB.
Covers outcome scoring (score_outcomes), per-source attribution, and the
prompt-ready track_record summary. No network: price/SPY lookups are injected.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.portfolio.journal import Journal
from src.portfolio.scorecard import Scorecard


@pytest.fixture
def journal(tmp_path):
    return Journal(db_path=tmp_path / "trades.db")


@pytest.fixture
def card(journal):
    """Scorecard pointed at the same DB the journal logs into."""
    return Scorecard(db_path=journal.db_path)


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _log(journal, ticker="NVDA", rec="BUY", days_ago=45, source="grok_x",
         confidence="HIGH", score=1.5) -> int:
    """Log a signal with a transaction_date `days_ago` in the past."""
    trade = {
        "ticker": ticker,
        "final_signal": rec,
        "score": score,
        "adjusted_score": score,
        "representative": "Nancy Pelosi",
        "amount_range": "$50,001 - $100,000",
        "transaction_date": _days_ago(days_ago),
        "sentiment": {"source": source, "label": "Bullish", "score": 0.4},
    }
    parsed = {
        "RECOMMENDATION": rec,
        "CONFIDENCE": confidence,
        "POSITION_SIZE": "3% of portfolio",
        "STOP_LOSS": "-5%",
        "TAKE_PROFIT": "+15%",
        "REASONING": "test",
        "RISK_NOTE": "test",
    }
    return journal.log_signal(trade, parsed, source="dry_run")


# ── score_outcomes ───────────────────────────────────────────────────────────

class TestScoreOutcomes:
    def test_buy_winner_recorded(self, journal, card):
        _log(journal, rec="BUY", days_ago=45)
        res = card.score_outcomes(
            horizon_days=30,
            price_fn=lambda t, d, h: 0.10,   # +10%
            spy_fn=lambda d, h: 0.02,        # SPY +2%
        )
        assert res["scored"] == 1
        assert res["wins"] == 1 and res["losses"] == 0

        attr = card.attribution(30)
        assert attr["scored_signals"] == 1
        bucket = attr["by_recommendation"][0]
        assert bucket["bucket"] == "BUY"
        assert bucket["avg_return_pct"] == pytest.approx(10.0, abs=0.01)
        assert bucket["avg_excess_pct"] == pytest.approx(8.0, abs=0.01)
        assert bucket["beat_spy_pct"] == 100.0

    def test_buy_loser_recorded(self, journal, card):
        _log(journal, rec="BUY", days_ago=45)
        res = card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: -0.06, spy_fn=lambda d, h: 0.01
        )
        assert res["wins"] == 0 and res["losses"] == 1

    def test_sell_is_sign_adjusted(self, journal, card):
        # A SELL that's right: price falls 5% → positive signal return.
        _log(journal, rec="SELL", days_ago=45)
        card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: -0.05, spy_fn=lambda d, h: 0.01
        )
        attr = card.attribution(30)
        bucket = attr["by_recommendation"][0]
        assert bucket["bucket"] == "SELL"
        assert bucket["avg_return_pct"] == pytest.approx(5.0, abs=0.01)   # -(-5%)
        # directional excess = +5% - (-1%) = +6%
        assert bucket["avg_excess_pct"] == pytest.approx(6.0, abs=0.01)

    def test_immature_signal_not_scored(self, journal, card):
        # Window hasn't elapsed yet — only 5 days old, horizon 30.
        _log(journal, rec="BUY", days_ago=5)
        res = card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: 0.10, spy_fn=lambda d, h: 0.0
        )
        assert res["scored"] == 0

    def test_hold_not_scored(self, journal, card):
        _log(journal, rec="HOLD", days_ago=45)
        res = card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: 0.10, spy_fn=lambda d, h: 0.0
        )
        assert res["scored"] == 0

    def test_missing_price_skipped_not_stored(self, journal, card):
        _log(journal, rec="BUY", days_ago=45)
        res = card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: None, spy_fn=lambda d, h: 0.0
        )
        assert res["scored"] == 0 and res["skipped_no_price"] == 1
        # Not stored → re-runnable later once price is available.
        assert card.attribution(30)["scored_signals"] == 0

    def test_idempotent(self, journal, card):
        _log(journal, rec="BUY", days_ago=45)
        first = card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: 0.10, spy_fn=lambda d, h: 0.0
        )
        second = card.score_outcomes(
            horizon_days=30, price_fn=lambda t, d, h: 0.10, spy_fn=lambda d, h: 0.0
        )
        assert first["scored"] == 1 and second["scored"] == 0
        assert card.attribution(30)["scored_signals"] == 1

    def test_multiple_horizons_independent(self, journal, card):
        _log(journal, rec="BUY", days_ago=100)
        card.score_outcomes(horizon_days=30, price_fn=lambda t, d, h: 0.05, spy_fn=lambda d, h: 0.0)
        card.score_outcomes(horizon_days=90, price_fn=lambda t, d, h: 0.12, spy_fn=lambda d, h: 0.0)
        assert card.attribution(30)["scored_signals"] == 1
        assert card.attribution(90)["scored_signals"] == 1


# ── attribution ──────────────────────────────────────────────────────────────

class TestAttribution:
    def test_breaks_down_by_source(self, journal, card):
        _log(journal, ticker="NVDA", source="grok_x", days_ago=45)
        _log(journal, ticker="AAPL", source="alpha_vantage", days_ago=45)

        def price(t, d, h):
            return 0.10 if t == "NVDA" else -0.04

        card.score_outcomes(horizon_days=30, price_fn=price, spy_fn=lambda d, h: 0.0)
        attr = card.attribution(30)
        sources = {b["bucket"]: b for b in attr["by_source"]}
        assert sources["grok_x"]["avg_excess_pct"] == pytest.approx(10.0, abs=0.01)
        assert sources["alpha_vantage"]["avg_excess_pct"] == pytest.approx(-4.0, abs=0.01)
        # Sorted best-first.
        assert attr["by_source"][0]["bucket"] == "grok_x"

    def test_empty_when_nothing_scored(self, journal, card):
        attr = card.attribution(30)
        assert attr["scored_signals"] == 0
        assert attr["by_source"] == []


# ── track_record ─────────────────────────────────────────────────────────────

class TestTrackRecord:
    def test_empty_string_with_no_history(self, journal, card):
        assert card.track_record(horizon_days=30) == ""

    def test_summarises_overall_and_source(self, journal, card):
        _log(journal, ticker="NVDA", source="grok_x", days_ago=45)
        _log(journal, ticker="MSFT", source="grok_x", days_ago=45)
        card.score_outcomes(horizon_days=30, price_fn=lambda t, d, h: 0.08, spy_fn=lambda d, h: 0.01)
        tr = card.track_record(horizon_days=30)
        assert "win rate" in tr
        assert "grok_x" in tr          # n>=2 so the source line appears
        assert "vs SPY" in tr

    def test_ticker_specific_line(self, journal, card):
        _log(journal, ticker="NVDA", days_ago=45)
        card.score_outcomes(horizon_days=30, price_fn=lambda t, d, h: 0.08, spy_fn=lambda d, h: 0.0)
        tr = card.track_record(ticker="NVDA", horizon_days=30)
        assert "NVDA" in tr
