"""
Massive (formerly Polygon.io) data integration for AI.Trader.

Free tier: unlimited API calls, 15-min delayed quotes, full historical data.
Existing Polygon.io API keys work unchanged — base URL stays api.polygon.io.

Provides:
  - News / sentiment       → replaces Alpha Vantage (25-call/day limit)
  - RSI + MACD             → short-run technical signals (new capability)
  - Price snapshot         → current price for position sizing
  - Fundamentals           → income statement, balance sheet

Set in .env:
  POLYGON_API_KEY=your_key   # same key as before rebrand

Sign up free: https://massive.com  (formerly polygon.io)
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
logger = logging.getLogger(__name__)

# api.polygon.io still works; api.massive.com is the new URL (both valid)
_BASE = "https://api.polygon.io"
_KEY  = os.getenv("POLYGON_API_KEY", "")

_CACHE_DIR = Path(__file__).parents[2] / "data" / "cache" / "massive"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

if not _KEY:
    logger.debug("POLYGON_API_KEY not set — Massive/Polygon data unavailable")


def _cache_get(key: str, ttl_hours: float = 1.0) -> Optional[dict]:
    p = _CACHE_DIR / f"{key}.json"
    if not p.exists():
        return None
    if (time.time() - p.stat().st_mtime) > ttl_hours * 3600:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _cache_set(key: str, data: dict) -> None:
    try:
        with open(_CACHE_DIR / f"{key}.json", "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def _get(path: str, params: dict = None) -> Optional[dict]:
    if not _KEY:
        return None
    p = {"apiKey": _KEY, **(params or {})}
    try:
        r = requests.get(f"{_BASE}{path}", params=p, timeout=15)
        if r.status_code in (401, 403):
            logger.debug("Massive: auth failed for %s — check POLYGON_API_KEY", path)
            return None
        if r.status_code == 429:
            logger.debug("Massive: rate limit on %s", path)
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.debug("Massive request failed %s: %s", path, e)
        return None


# ── news / sentiment ──────────────────────────────────────────────────────────

def get_news(ticker: str, limit: int = 10, days_back: int = 7) -> list:
    """
    Fetch recent news articles for a ticker via Massive (Polygon) news API.
    Free tier: no rate limit. Replaces Alpha Vantage news endpoint.
    """
    cache_key = f"news_{ticker}_{days_back}d"
    cached = _cache_get(cache_key, ttl_hours=2)
    if cached is not None:
        return cached

    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    data = _get("/v2/reference/news", {
        "ticker": ticker.upper(),
        "limit": limit,
        "published_utc.gte": cutoff,
        "order": "desc",
        "sort": "published_utc",
    })
    if not data:
        return []

    articles = data.get("results", [])
    result = []
    for a in articles:
        insights = a.get("insights", [])
        ticker_insight = next((i for i in insights if i.get("ticker") == ticker.upper()), {})
        sentiment_label = ticker_insight.get("sentiment", "neutral").lower()
        score_map = {"positive": 0.5, "negative": -0.5, "neutral": 0.0}
        result.append({
            "title": a.get("title", ""),
            "published": a.get("published_utc", "")[:10],
            "source": a.get("publisher", {}).get("name", ""),
            "url": a.get("article_url", ""),
            "ticker_sentiment": sentiment_label,
            "ticker_score": score_map.get(sentiment_label, 0.0),
        })

    _cache_set(cache_key, result)
    return result


def get_news_sentiment(ticker: str, limit: int = 10) -> dict:
    """
    Summarize news sentiment for a ticker.
    Returns same schema as Alpha Vantage sentiment (drop-in replacement).
    """
    articles = get_news(ticker, limit=limit)
    if not articles:
        return {"label": "Neutral", "score": 0.0, "articles": 0, "source": "massive"}

    scores = [a["ticker_score"] for a in articles]
    avg = sum(scores) / len(scores) if scores else 0.0

    if avg >= 0.15:
        label = "Bullish"
    elif avg <= -0.15:
        label = "Bearish"
    else:
        label = "Neutral"

    return {
        "label": label,
        "score": round(avg, 4),
        "articles": len(articles),
        "source": "massive",
    }


# ── technical indicators ─────────────────────────────────────────────────────

def get_rsi(ticker: str, window: int = 14, timespan: str = "day") -> Optional[dict]:
    """
    Fetch RSI for a ticker. window=14 daily is standard.
    Returns {'value': float, 'signal': 'overbought'|'oversold'|'neutral'}.
    """
    cache_key = f"rsi_{ticker}_{window}{timespan}"
    cached = _cache_get(cache_key, ttl_hours=4)
    if cached is not None:
        return cached

    data = _get(f"/v1/indicators/rsi/{ticker.upper()}", {
        "timespan": timespan,
        "window": window,
        "series_type": "close",
        "order": "desc",
        "limit": 1,
    })
    if not data:
        return None

    results = data.get("results", {}).get("values", [])
    if not results:
        return None

    rsi_val = float(results[0].get("value", 50))
    signal = (
        "overbought" if rsi_val >= 70
        else "oversold" if rsi_val <= 30
        else "neutral"
    )
    result = {
        "value": round(rsi_val, 2),
        "signal": signal,
        "timestamp": results[0].get("timestamp"),
    }
    _cache_set(cache_key, result)
    return result


def get_macd(ticker: str, timespan: str = "day") -> Optional[dict]:
    """
    Fetch MACD (12/26/9) for a ticker.
    Returns {'macd': float, 'signal': float, 'histogram': float, 'crossover': str}.
    """
    cache_key = f"macd_{ticker}_{timespan}"
    cached = _cache_get(cache_key, ttl_hours=4)
    if cached is not None:
        return cached

    data = _get(f"/v1/indicators/macd/{ticker.upper()}", {
        "timespan": timespan,
        "short_window": 12,
        "long_window": 26,
        "signal_window": 9,
        "series_type": "close",
        "order": "desc",
        "limit": 2,
    })
    if not data:
        return None

    values = data.get("results", {}).get("values", [])
    if not values:
        return None

    latest = values[0]
    macd_val = float(latest.get("value", 0))
    sig_val  = float(latest.get("signal", 0))
    hist_val = float(latest.get("histogram", 0))

    # Detect crossover if we have 2 bars
    crossover = "none"
    if len(values) >= 2:
        prev_hist = float(values[1].get("histogram", 0))
        if prev_hist < 0 and hist_val >= 0:
            crossover = "bullish"
        elif prev_hist > 0 and hist_val <= 0:
            crossover = "bearish"

    result = {
        "macd": round(macd_val, 4),
        "signal_line": round(sig_val, 4),
        "histogram": round(hist_val, 4),
        "crossover": crossover,
        "bias": "bullish" if macd_val > sig_val else "bearish",
    }
    _cache_set(cache_key, result)
    return result


def get_sma(ticker: str, window: int = 50, timespan: str = "day") -> Optional[float]:
    """Return latest SMA value. Useful for trend direction."""
    data = _get(f"/v1/indicators/sma/{ticker.upper()}", {
        "timespan": timespan,
        "window": window,
        "series_type": "close",
        "order": "desc",
        "limit": 1,
    })
    if not data:
        return None
    values = data.get("results", {}).get("values", [])
    return float(values[0]["value"]) if values else None


# ── price snapshot ────────────────────────────────────────────────────────────

def get_price_snapshot(ticker: str) -> Optional[dict]:
    """
    Fetch latest price snapshot (15-min delayed on free tier).
    Returns {'price': float, 'change_pct': float, 'volume': int}.
    """
    data = _get(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}")
    if not data:
        return None
    ticker_data = data.get("ticker", {})
    day = ticker_data.get("day", {})
    prev = ticker_data.get("prevDay", {})
    price = day.get("c") or ticker_data.get("lastTrade", {}).get("p")
    prev_close = prev.get("c")
    change_pct = ((price - prev_close) / prev_close * 100) if price and prev_close else None
    return {
        "price": price,
        "change_pct": round(change_pct, 2) if change_pct else None,
        "volume": day.get("v"),
        "open": day.get("o"),
        "high": day.get("h"),
        "low":  day.get("l"),
    }


# ── technical signal summary (for Claude) ────────────────────────────────────

def get_technical_context(ticker: str) -> str:
    """
    Return formatted technical analysis block for Claude's prompt.
    Empty string if no API key or data unavailable.
    """
    if not _KEY:
        return ""

    ticker = ticker.upper()
    parts = []

    rsi = get_rsi(ticker)
    if rsi:
        parts.append(
            f"  RSI(14): {rsi['value']} → {rsi['signal'].upper()}"
            + (" — potential reversal" if rsi["signal"] != "neutral" else "")
        )

    macd = get_macd(ticker)
    if macd:
        cross_str = f" [{macd['crossover'].upper()} CROSSOVER]" if macd["crossover"] != "none" else ""
        parts.append(
            f"  MACD: {macd['macd']:+.3f} vs signal {macd['signal_line']:+.3f} "
            f"(hist={macd['histogram']:+.3f}) → {macd['bias'].upper()}{cross_str}"
        )

    snap = get_price_snapshot(ticker)
    if snap and snap.get("price"):
        chg = f" ({snap['change_pct']:+.1f}% today)" if snap.get("change_pct") else ""
        parts.append(f"  Price: ${snap['price']:.2f}{chg}")

    if not parts:
        return ""

    return "\nTechnical Analysis (Massive/Polygon):\n" + "\n".join(parts)


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

    print(f"=== Massive data for {t} ===\n")

    news = get_news(t, limit=5)
    sent = get_news_sentiment(t)
    print(f"News: {len(news)} articles | Sentiment: {sent['label']} (score={sent['score']})")

    rsi = get_rsi(t)
    print(f"RSI(14): {rsi['value'] if rsi else 'N/A'} → {rsi['signal'] if rsi else 'N/A'}")

    macd = get_macd(t)
    if macd:
        print(f"MACD: {macd['macd']:+.4f} | Bias: {macd['bias']} | Crossover: {macd['crossover']}")

    ctx = get_technical_context(t)
    print(ctx)
