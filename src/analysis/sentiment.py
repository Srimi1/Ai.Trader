"""
News sentiment layer.

Source priority:
  0. Grok/X (xAI) — real-time X/Twitter, unlimited              [GROK_API_KEY]
  1. Massive (Polygon.io) — unlimited free calls, no rate limit  [POLYGON_API_KEY]
  2. Alpha Vantage — 25 calls/day fallback                        [ALPHA_VANTAGE_KEY]
  3. Neutral fallback — pipeline never crashes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))


SENTIMENT_MULTIPLIERS = {
    "Bullish": 1.5,
    "Somewhat-Bullish": 1.2,
    "Neutral": 1.0,
    "Somewhat-Bearish": 0.7,
    "Bearish": 0.5,
}


def get_sentiment_multiplier(ticker: str) -> dict:
    # 0. Try Grok/X (real-time X/Twitter, unlimited calls)
    try:
        from src.ingestion.xsocial import get_x_sentiment, _KEY as _grok_key
        if _grok_key:
            result = get_x_sentiment(ticker)
            label = result["label"]
            return {
                "ticker": ticker,
                "label": label,
                "score": result["score"],
                "multiplier": SENTIMENT_MULTIPLIERS.get(label, 1.0),
                "articles": result["articles"],
                "source": "grok_x",
                "themes": result.get("themes", []),
            }
    except Exception:
        pass

    # 1. Try Massive/Polygon (unlimited free, no rate limit)
    try:
        from src.ingestion.massive import get_news_sentiment, _KEY as _polygon_key
        if _polygon_key:
            result = get_news_sentiment(ticker, limit=10)
            label = result["label"]
            return {
                "ticker": ticker,
                "label": label,
                "score": result["score"],
                "multiplier": SENTIMENT_MULTIPLIERS.get(label, 1.0),
                "articles": result["articles"],
                "source": "massive",
            }
    except Exception:
        pass

    # 2. Fall back to Alpha Vantage
    try:
        from src.ingestion.news import get_average_sentiment
        result = get_average_sentiment(ticker, limit=20)
        label = result["label"]
        return {
            "ticker": ticker,
            "label": label,
            "score": result["score"],
            "multiplier": SENTIMENT_MULTIPLIERS.get(label, 1.0),
            "articles": result["articles"],
            "source": "alpha_vantage",
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "label": "Neutral",
            "score": 0.0,
            "multiplier": 1.0,
            "articles": 0,
            "source": "fallback",
            "error": str(e),
        }


def apply_sentiment(scored_trades: list[dict]) -> list[dict]:
    cache: dict[str, dict] = {}
    result = []
    for trade in scored_trades:
        ticker = trade["ticker"]
        if ticker not in cache:
            cache[ticker] = get_sentiment_multiplier(ticker)
        sentiment = cache[ticker]
        adjusted_score = trade["score"] * sentiment["multiplier"]
        result.append({
            **trade,
            "sentiment": sentiment,
            "adjusted_score": round(adjusted_score, 3),
            "final_signal": "BUY" if adjusted_score > 0.5 else ("SELL" if adjusted_score < -0.5 else "NEUTRAL"),
        })
    return sorted(result, key=lambda x: abs(x["adjusted_score"]), reverse=True)


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    s = get_sentiment_multiplier(ticker)
    print(f"{ticker}: {s['label']} (multiplier={s['multiplier']}, score={s['score']})")
