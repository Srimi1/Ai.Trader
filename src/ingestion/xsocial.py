"""
X/Twitter social intelligence via xAI Grok API.

Grok has native real-time X search built in — no extra parameters needed.
Uses OpenAI-compatible SDK pointed at api.x.ai.

Sentiment chain position: Tier 0 (before Massive/Polygon, before Alpha Vantage).

Env var: GROK_API_KEY
"""
import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

logger = logging.getLogger(__name__)

_KEY = os.getenv("GROK_API_KEY", "")
_BASE = "https://api.x.ai/v1"
_MODEL_FAST = "grok-3-mini"
_MODEL_DEEP = "grok-2-latest"

_client = None


def _get_client():
    global _client
    if _client is None:
        if not _KEY:
            raise RuntimeError("GROK_API_KEY not set")
        from openai import OpenAI
        _client = OpenAI(api_key=_KEY, base_url=_BASE)
    return _client


def _parse_json(text: str) -> dict:
    """Extract first JSON object from Grok response."""
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON found in response: {text[:300]}")


def get_x_sentiment(ticker: str, limit: int = 20) -> dict:
    """
    Real-time X/Twitter sentiment for a ticker using Grok live search.

    Returns schema matching massive.py and news.py:
        {label, score, articles, source, themes}
    """
    client = _get_client()
    prompt = (
        f"Search X (Twitter) for the most recent {limit} posts about the stock ${ticker}. "
        "Analyze their sentiment and return ONLY this JSON — no explanation, no markdown:\n"
        '{"label": "Bullish" or "Neutral" or "Bearish", '
        '"score": <float between -1.0 and 1.0>, '
        '"posts_analyzed": <integer>, '
        '"key_themes": ["theme1", "theme2", "theme3"]}'
    )
    response = client.chat.completions.create(
        model=_MODEL_FAST,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
    )
    text = response.choices[0].message.content or ""
    data = _parse_json(text)

    label = data.get("label", "Neutral")
    if label not in ("Bullish", "Somewhat-Bullish", "Neutral", "Somewhat-Bearish", "Bearish"):
        label = "Neutral"
    score = max(-1.0, min(1.0, float(data.get("score", 0.0))))

    return {
        "label": label,
        "score": round(score, 4),
        "articles": int(data.get("posts_analyzed", 0)),
        "source": "grok_x",
        "themes": data.get("key_themes", []),
    }


def get_politician_x_activity(politician: str, ticker: str) -> str:
    """
    Search X for recent public posts by or about a congress member
    related to a stock ticker or its sector.

    Returns a 2-3 sentence plaintext summary for injection into Claude prompt.
    Returns empty string on any failure.
    """
    if not politician or not ticker:
        return ""
    client = _get_client()
    prompt = (
        f"Search X for recent posts by or about {politician} (US Congress member) "
        f"related to {ticker} or its industry sector. "
        "Summarize in 2-3 sentences what they have said publicly. "
        "If nothing is found, respond with exactly: 'No relevant X activity found.' "
        "Cite only what you find — do not infer."
    )
    response = client.chat.completions.create(
        model=_MODEL_FAST,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def get_market_narrative(ticker: str) -> str:
    """
    Get a concise market narrative from X for a ticker using Grok deep search.
    Used optionally for --deep-analysis mode.
    """
    client = _get_client()
    prompt = (
        f"Search X and financial news for {ticker}. "
        "In 3-4 sentences: what is the dominant narrative right now? "
        "What are bulls saying? What are bears saying? What event is most discussed?"
    )
    response = client.chat.completions.create(
        model=_MODEL_DEEP,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print(f"\nX Sentiment for {t}:")
    print(get_x_sentiment(t))
    print(f"\nMarket Narrative:")
    print(get_market_narrative(t))
