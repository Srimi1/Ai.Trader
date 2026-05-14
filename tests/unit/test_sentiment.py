"""Unit tests for sentiment layer — mocked API."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.analysis.sentiment import get_sentiment_multiplier, apply_sentiment, SENTIMENT_MULTIPLIERS
from tests.fixtures.sample_trades import SAMPLE_NORMALIZED_TRADES


class TestGetSentimentMultiplier:
    # sentiment.py now imports lazily inside the function.
    # Block Grok (Tier 0), Massive (Tier 1) — test only Alpha Vantage (Tier 2) path.
    @patch("src.ingestion.news.get_average_sentiment")
    @patch("src.ingestion.massive._KEY", "")
    @patch("src.ingestion.xsocial._KEY", "")
    def test_bullish_returns_1_5(self, mock_sent):
        mock_sent.return_value = {"label": "Bullish", "score": 0.4, "articles": 15}
        result = get_sentiment_multiplier("NVDA")
        assert result["multiplier"] == 1.5
        assert result["label"] == "Bullish"

    @patch("src.ingestion.news.get_average_sentiment")
    @patch("src.ingestion.massive._KEY", "")
    @patch("src.ingestion.xsocial._KEY", "")
    def test_bearish_returns_0_5(self, mock_sent):
        mock_sent.return_value = {"label": "Bearish", "score": -0.4, "articles": 10}
        result = get_sentiment_multiplier("NVDA")
        assert result["multiplier"] == 0.5

    @patch("src.ingestion.news.get_average_sentiment")
    @patch("src.ingestion.massive._KEY", "")
    @patch("src.ingestion.xsocial._KEY", "")
    def test_neutral_returns_1_0(self, mock_sent):
        mock_sent.return_value = {"label": "Neutral", "score": 0.0, "articles": 5}
        result = get_sentiment_multiplier("NVDA")
        assert result["multiplier"] == 1.0

    @patch("src.ingestion.news.get_average_sentiment")
    @patch("src.ingestion.massive._KEY", "")
    @patch("src.ingestion.xsocial._KEY", "")
    def test_api_failure_returns_fallback(self, mock_sent):
        mock_sent.side_effect = Exception("API down")
        result = get_sentiment_multiplier("NVDA")
        assert result["multiplier"] == 1.0
        assert result["label"] == "Neutral"
        assert result["source"] == "fallback"
        assert "error" in result

    @patch("src.ingestion.xsocial.get_x_sentiment")
    @patch("src.ingestion.xsocial._KEY", "xai-test")
    @patch("src.ingestion.massive._KEY", "")
    def test_grok_tier0_used_when_key_set(self, mock_grok):
        mock_grok.return_value = {
            "label": "Bullish", "score": 0.82, "articles": 25,
            "source": "grok_x", "themes": ["AI rally"],
        }
        result = get_sentiment_multiplier("NVDA")
        assert result["source"] == "grok_x"
        assert result["multiplier"] == 1.5
        assert result["themes"] == ["AI rally"]

    def test_all_labels_covered(self):
        for label in SENTIMENT_MULTIPLIERS:
            assert SENTIMENT_MULTIPLIERS[label] > 0


class TestApplySentiment:
    @patch("src.analysis.sentiment.get_sentiment_multiplier")
    def test_adjusts_score(self, mock_mult):
        mock_mult.return_value = {
            "ticker": "NVDA", "label": "Bullish", "score": 0.4,
            "multiplier": 1.5, "articles": 10, "source": "alpha_vantage",
        }
        trade = {**SAMPLE_NORMALIZED_TRADES[0], "score": 1.0}
        results = apply_sentiment([trade])
        assert results[0]["adjusted_score"] == pytest.approx(1.5, rel=0.01)

    @patch("src.analysis.sentiment.get_sentiment_multiplier")
    def test_caches_per_ticker(self, mock_mult):
        mock_mult.return_value = {
            "ticker": "NVDA", "label": "Neutral", "score": 0.0,
            "multiplier": 1.0, "articles": 5, "source": "alpha_vantage",
        }
        trades = [
            {**SAMPLE_NORMALIZED_TRADES[0], "ticker": "NVDA"},
            {**SAMPLE_NORMALIZED_TRADES[0], "ticker": "NVDA"},
        ]
        apply_sentiment(trades)
        assert mock_mult.call_count == 1  # cached after first call

    @patch("src.analysis.sentiment.get_sentiment_multiplier")
    def test_final_signal_buy(self, mock_mult):
        mock_mult.return_value = {
            "ticker": "NVDA", "label": "Bullish", "score": 0.4,
            "multiplier": 1.5, "articles": 10, "source": "alpha_vantage",
        }
        trade = {**SAMPLE_NORMALIZED_TRADES[0], "score": 1.0}
        results = apply_sentiment([trade])
        assert results[0]["final_signal"] == "BUY"

    @patch("src.analysis.sentiment.get_sentiment_multiplier")
    def test_sorted_by_adjusted_score_desc(self, mock_mult):
        mock_mult.side_effect = lambda ticker: {
            "ticker": ticker, "label": "Neutral", "score": 0.0,
            "multiplier": 1.0, "articles": 5, "source": "alpha_vantage",
        }
        results = apply_sentiment(SAMPLE_NORMALIZED_TRADES[:3])
        scores = [abs(r["adjusted_score"]) for r in results]
        assert scores == sorted(scores, reverse=True)
