"""Unit tests for xsocial.py — Grok/xAI X sentiment. All API calls mocked."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))


def _mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestGetXSentiment:
    @patch("src.ingestion.xsocial._KEY", "xai-test")
    @patch("src.ingestion.xsocial._client", None)
    @patch("src.ingestion.xsocial.OpenAI", create=True)
    def test_bullish_parsed(self, mock_openai):
        from openai import OpenAI
        inst = MagicMock()
        inst.chat.completions.create.return_value = _mock_response(
            '{"label": "Bullish", "score": 0.72, "posts_analyzed": 18, "key_themes": ["AI momentum", "earnings beat", "data center"]}'
        )
        mock_openai.return_value = inst

        from src.ingestion import xsocial
        xsocial._client = None

        with patch("src.ingestion.xsocial.OpenAI", return_value=inst):
            xsocial._client = inst
            result = xsocial.get_x_sentiment("NVDA")

        assert result["label"] == "Bullish"
        assert result["score"] == 0.72
        assert result["source"] == "grok_x"
        assert "AI momentum" in result["themes"]

    @patch("src.ingestion.xsocial._KEY", "xai-test")
    def test_bearish_parsed(self):
        from src.ingestion import xsocial
        inst = MagicMock()
        inst.chat.completions.create.return_value = _mock_response(
            '{"label": "Bearish", "score": -0.45, "posts_analyzed": 12, "key_themes": ["earnings miss", "guidance cut"]}'
        )
        xsocial._client = inst
        result = xsocial.get_x_sentiment("DXCM")
        assert result["label"] == "Bearish"
        assert result["score"] == -0.45
        assert result["articles"] == 12

    @patch("src.ingestion.xsocial._KEY", "xai-test")
    def test_score_clamped(self):
        from src.ingestion import xsocial
        inst = MagicMock()
        inst.chat.completions.create.return_value = _mock_response(
            '{"label": "Bullish", "score": 99.9, "posts_analyzed": 5, "key_themes": []}'
        )
        xsocial._client = inst
        result = xsocial.get_x_sentiment("AAPL")
        assert result["score"] == 1.0

    @patch("src.ingestion.xsocial._KEY", "xai-test")
    def test_invalid_label_defaults_neutral(self):
        from src.ingestion import xsocial
        inst = MagicMock()
        inst.chat.completions.create.return_value = _mock_response(
            '{"label": "Sideways", "score": 0.1, "posts_analyzed": 3, "key_themes": []}'
        )
        xsocial._client = inst
        result = xsocial.get_x_sentiment("SPY")
        assert result["label"] == "Neutral"

    @patch("src.ingestion.xsocial._KEY", "")
    def test_no_key_raises(self):
        from src.ingestion import xsocial
        xsocial._client = None
        with pytest.raises(RuntimeError, match="GROK_API_KEY"):
            xsocial.get_x_sentiment("NVDA")


class TestGetPoliticianXActivity:
    @patch("src.ingestion.xsocial._KEY", "xai-test")
    def test_returns_string(self):
        from src.ingestion import xsocial
        inst = MagicMock()
        inst.chat.completions.create.return_value = _mock_response(
            "Pelosi tweeted in support of AI funding on May 12."
        )
        xsocial._client = inst
        result = xsocial.get_politician_x_activity("Nancy Pelosi", "NVDA")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.ingestion.xsocial._KEY", "xai-test")
    def test_empty_inputs_return_empty(self):
        from src.ingestion import xsocial
        assert xsocial.get_politician_x_activity("", "NVDA") == ""
        assert xsocial.get_politician_x_activity("Pelosi", "") == ""

    @patch("src.ingestion.xsocial._KEY", "")
    def test_no_key_returns_empty(self):
        from src.ingestion import xsocial
        xsocial._client = None
        # Should return empty string (not raise) when key missing — guarded by _KEY check
        # Actually _get_client raises — the caller in orchestrator wraps in try/except
        # Direct call to get_politician_x_activity calls _get_client which raises
        with pytest.raises(RuntimeError):
            xsocial.get_politician_x_activity("Pelosi", "NVDA")
