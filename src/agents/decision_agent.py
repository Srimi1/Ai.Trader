"""Claude-powered decision agent: takes scored + sentiment-enriched trade → BUY/HOLD/SELL."""
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

SYSTEM_PROMPT = """You are a US equity trading analyst specializing in political alpha signals.
You analyze congressional stock disclosures (STOCK Act filings) and produce actionable trade recommendations.

Your inputs per trade:
- Politician name and their influence level
- Ticker, trade type (purchase/sale), amount range
- Signal score (higher = stronger signal; negative = bearish)
- News sentiment from Alpha Vantage
- Number of politicians who bought the same ticker recently (cluster)

Your output must be structured exactly as:
RECOMMENDATION: [BUY | HOLD | SELL]
CONFIDENCE: [HIGH | MEDIUM | LOW]
POSITION_SIZE: [1-5]% of portfolio
STOP_LOSS: -[X]%
TAKE_PROFIT: +[X]%
REASONING: <2-3 sentences explaining the thesis>
RISK_NOTE: <one sentence on key risk>"""


def get_recommendation(trade: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    sentiment = trade.get("sentiment", {})
    components = trade.get("score_components", {})

    user_msg = f"""Congressional Trade Signal:

Politician: {trade['representative']}
Ticker: {trade['ticker']}
Trade Type: {trade['trade_type'].upper()}
Amount: {trade['amount_range']}
Transaction Date: {trade['transaction_date']}
Disclosure Date: {trade.get('disclosure_date', 'N/A')}

Signal Score: {trade['score']:+.3f} (adjusted: {trade.get('adjusted_score', trade['score']):+.3f})
Score Components:
  - Politician weight: {components.get('politician', 1.0):.2f}
  - Amount weight: {components.get('amount', 1.0):.2f}
  - Recency weight: {components.get('recency', 1.0):.2f}
  - Cluster bonus: {components.get('cluster', 1.0):.2f}

News Sentiment: {sentiment.get('label', 'Unknown')} (score={sentiment.get('score', 0):.3f}, n={sentiment.get('articles', 0)} articles)

Provide your recommendation."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = message.content[0].text
    return {"ticker": trade["ticker"], "raw": raw, "trade": trade}


def parse_recommendation(raw: str) -> dict:
    lines = raw.strip().split("\n")
    result = {}
    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result
