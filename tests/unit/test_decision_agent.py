"""Unit tests for decision agent parsing — no API calls."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.agents.decision_agent import parse_recommendation


SAMPLE_RAW = """RECOMMENDATION: BUY
CONFIDENCE: HIGH
POSITION_SIZE: 3% of portfolio
STOP_LOSS: -5%
TAKE_PROFIT: +15%
REASONING: Nancy Pelosi's purchase of NVDA during a period of strong AI tailwinds signals insider conviction. The $100K+ position size and 5-day-old disclosure maximize recency and cluster score.
RISK_NOTE: Sector rotation into defensives could limit upside if macro conditions deteriorate."""

SELL_RAW = """RECOMMENDATION: SELL
CONFIDENCE: MEDIUM
POSITION_SIZE: 2% of portfolio
STOP_LOSS: -4%
TAKE_PROFIT: +8%
REASONING: Senator McCaul's full sale of AMZN into strength may signal near-term peak.
RISK_NOTE: Could be a portfolio rebalance unrelated to fundamental view."""


class TestParseRecommendation:
    def test_buy_parsed(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert result["RECOMMENDATION"] == "BUY"

    def test_confidence_parsed(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert result["CONFIDENCE"] == "HIGH"

    def test_position_size_parsed(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert "3%" in result["POSITION_SIZE"]

    def test_stop_loss_parsed(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert "-5%" in result["STOP_LOSS"]

    def test_take_profit_parsed(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert "+15%" in result["TAKE_PROFIT"]

    def test_reasoning_nonempty(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert len(result.get("REASONING", "")) > 10

    def test_risk_note_nonempty(self):
        result = parse_recommendation(SAMPLE_RAW)
        assert len(result.get("RISK_NOTE", "")) > 5

    def test_sell_parsed(self):
        result = parse_recommendation(SELL_RAW)
        assert result["RECOMMENDATION"] == "SELL"

    def test_returns_dict(self):
        assert isinstance(parse_recommendation(SAMPLE_RAW), dict)

    def test_empty_string_returns_empty_dict(self):
        result = parse_recommendation("")
        assert isinstance(result, dict)
