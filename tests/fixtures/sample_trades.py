"""Shared test fixtures — no network, no API keys required."""
from datetime import datetime, timedelta


def make_raw_trade(
    representative="Nancy Pelosi",
    ticker="NVDA",
    transaction="Purchase",
    amount_range="$50,001 - $100,000",
    days_ago=10,
    house="Representatives",
    party="D",
):
    today = datetime.now()
    tx_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    disc_date = (today - timedelta(days=max(0, days_ago - 3))).strftime("%Y-%m-%d")
    return {
        "Representative": representative,
        "BioGuideID": "P000197",
        "ReportDate": disc_date,
        "TransactionDate": tx_date,
        "Ticker": ticker,
        "Transaction": transaction,
        "Range": amount_range,
        "House": house,
        "Party": party,
        "TickerType": "ST",
        "Description": None,
        "ExcessReturn": 4.5,
        "PriceChange": 2.1,
        "SPYChange": 0.8,
    }


def make_normalized_trade(
    representative="Nancy Pelosi",
    ticker="NVDA",
    trade_type="purchase",
    amount_range="$50,001 - $100,000",
    days_ago=10,
    score=1.2,
    adjusted_score=1.5,
    final_signal="BUY",
    source="house",
):
    today = datetime.now()
    tx_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    disc_date = (today - timedelta(days=max(0, days_ago - 3))).strftime("%Y-%m-%d")
    return {
        "source": source,
        "representative": representative,
        "ticker": ticker,
        "asset_description": "",
        "trade_type": trade_type,
        "amount_range": amount_range,
        "transaction_date": tx_date,
        "disclosure_date": disc_date,
        "district": "D",
        "excess_return": 4.5,
        "price_change": 2.1,
        "spy_change": 0.8,
        "score": score,
        "adjusted_score": adjusted_score,
        "final_signal": final_signal,
        "score_components": {
            "politician": 1.5,
            "amount": 1.2,
            "recency": 0.8,
            "cluster": 1.0,
        },
        "sentiment": {
            "label": "Bullish",
            "score": 0.35,
            "multiplier": 1.5,
            "articles": 12,
            "source": "alpha_vantage",
        },
    }


SAMPLE_RAW_TRADES = [
    make_raw_trade("Nancy Pelosi", "NVDA", "Purchase", "$100,001 - $250,000", days_ago=5),
    make_raw_trade("Dan Crenshaw", "MSFT", "Sale", "$15,001 - $50,000", days_ago=15),
    make_raw_trade("Tommy Tuberville", "AAPL", "Purchase", "$50,001 - $100,000", days_ago=25, house="Senate"),
    make_raw_trade("Ro Khanna", "TSLA", "Purchase", "$1,001 - $15,000", days_ago=8),
    make_raw_trade("Michael McCaul", "AMZN", "Sale (Full)", "$250,001 - $500,000", days_ago=40),
]

SAMPLE_NORMALIZED_TRADES = [
    make_normalized_trade("Nancy Pelosi", "NVDA", "purchase", "$100,001 - $250,000", days_ago=5, score=1.8, adjusted_score=2.1),
    make_normalized_trade("Dan Crenshaw", "MSFT", "sale", "$15,001 - $50,000", days_ago=15, score=-0.6, adjusted_score=-0.7, final_signal="SELL"),
    make_normalized_trade("Tommy Tuberville", "AAPL", "purchase", "$50,001 - $100,000", days_ago=25, score=0.9, adjusted_score=1.0),
    make_normalized_trade("Ro Khanna", "TSLA", "purchase", "$1,001 - $15,000", days_ago=8, score=0.4, adjusted_score=0.5),
    make_normalized_trade("Michael McCaul", "AMZN", "sale_full", "$250,001 - $500,000", days_ago=40, score=-1.2, adjusted_score=-0.6, final_signal="SELL"),
]
