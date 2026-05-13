"""News sentiment layer using Alpha Vantage (free tier) with FinGPT as optional upgrade."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.ingestion.news import get_average_sentiment


SENTIMENT_MULTIPLIERS = {
    "Bullish": 1.5,
    "Somewhat-Bullish": 1.2,
    "Neutral": 1.0,
    "Somewhat-Bearish": 0.7,
    "Bearish": 0.5,
}


def get_sentiment_multiplier(ticker: str) -> dict:
    try:
        result = get_average_sentiment(ticker, limit=20)
        label = result["label"]
        multiplier = SENTIMENT_MULTIPLIERS.get(label, 1.0)
        return {
            "ticker": ticker,
            "label": label,
            "score": result["score"],
            "multiplier": multiplier,
            "articles": result["articles"],
            "source": "alpha_vantage",
        }
    except Exception as e:
        # Fallback: neutral if API fails
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
