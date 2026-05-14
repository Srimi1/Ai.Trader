"""Integration test — real Anthropic API call (uses ANTHROPIC_API_KEY)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.agents.decision_agent import get_recommendation, parse_recommendation
from tests.fixtures.sample_trades import make_normalized_trade

pytestmark = pytest.mark.integration


@pytest.fixture
def sample_trade():
    t = make_normalized_trade("Nancy Pelosi", "NVDA", "purchase", "$100,001 - $250,000", days_ago=5)
    t["score"] = 1.8
    t["adjusted_score"] = 2.1
    t["final_signal"] = "BUY"
    return t


class TestGetRecommendation:
    def test_returns_dict_with_raw(self, sample_trade):
        result = get_recommendation(sample_trade)
        assert isinstance(result, dict)
        assert "raw" in result
        assert len(result["raw"]) > 50

    def test_ticker_in_result(self, sample_trade):
        result = get_recommendation(sample_trade)
        assert result["ticker"] == "NVDA"

    def test_raw_has_recommendation(self, sample_trade):
        result = get_recommendation(sample_trade)
        assert "RECOMMENDATION" in result["raw"]

    def test_parsed_recommendation_valid(self, sample_trade):
        result = get_recommendation(sample_trade)
        parsed = parse_recommendation(result["raw"])
        assert parsed.get("RECOMMENDATION") in ("BUY", "SELL", "HOLD")
        assert parsed.get("CONFIDENCE") in ("HIGH", "MEDIUM", "LOW")
