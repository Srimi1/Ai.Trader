"""Fetch news headlines via Alpha Vantage News API."""
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

AV_BASE = "https://www.alphavantage.co/query"


def get_news(ticker: str, limit: int = 10) -> list[dict]:
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise EnvironmentError("ALPHA_VANTAGE_KEY not set in .env")

    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "limit": limit,
        "sort": "LATEST",
        "apikey": api_key,
    }
    resp = requests.get(AV_BASE, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    articles = data.get("feed", [])
    results = []
    for a in articles:
        ticker_sentiment = next(
            (ts for ts in a.get("ticker_sentiment", []) if ts.get("ticker") == ticker),
            {},
        )
        results.append({
            "title": a.get("title", ""),
            "summary": a.get("summary", ""),
            "published": a.get("time_published", ""),
            "source": a.get("source", ""),
            "overall_sentiment": a.get("overall_sentiment_label", "Neutral"),
            "overall_score": float(a.get("overall_sentiment_score", 0)),
            "ticker_sentiment": ticker_sentiment.get("ticker_sentiment_label", "Neutral"),
            "ticker_score": float(ticker_sentiment.get("ticker_sentiment_score", 0)),
        })
    return results


def get_average_sentiment(ticker: str, limit: int = 20) -> dict:
    articles = get_news(ticker, limit=limit)
    if not articles:
        return {"label": "Neutral", "score": 0.0, "articles": 0}
    avg_score = sum(a["ticker_score"] for a in articles) / len(articles)
    if avg_score >= 0.15:
        label = "Bullish"
    elif avg_score <= -0.15:
        label = "Bearish"
    else:
        label = "Neutral"
    return {"label": label, "score": round(avg_score, 4), "articles": len(articles)}


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    sentiment = get_average_sentiment(ticker)
    print(f"{ticker} sentiment: {sentiment['label']} (score={sentiment['score']}, n={sentiment['articles']})")
