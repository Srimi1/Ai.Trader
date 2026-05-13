"""Score STOCK Act disclosures using committee weight, amount, recency, and cluster bonus."""
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parents[2] / "config" / "politicians.json"

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

AMOUNT_WEIGHTS = CONFIG["amount_weights"]
COMMITTEE_WEIGHTS = CONFIG["committee_weights"]
KNOWN_TRADERS = CONFIG["known_active_traders"]


def _amount_weight(amount_range: str) -> float:
    for key, weight in AMOUNT_WEIGHTS.items():
        if key in amount_range:
            return weight
    return 0.8


def _politician_weight(name: str) -> float:
    info = KNOWN_TRADERS.get(name, {})
    committee_role = info.get("committee", "unknown")
    base = COMMITTEE_WEIGHTS.get(committee_role, 1.0)
    bonus = info.get("weight_bonus", 1.0)
    return round(base * bonus, 3)


def _recency_weight(transaction_date: str) -> float:
    try:
        trade_date = datetime.strptime(transaction_date[:10], "%Y-%m-%d")
        days_ago = (datetime.now() - trade_date).days
        # exponential decay: 1.0 at day 0, ~0.1 at day 45
        return round(math.exp(-0.05 * days_ago), 3)
    except ValueError:
        return 0.5


def _cluster_bonus(ticker: str, all_trades: list[dict], window_days: int = 30) -> float:
    cutoff = datetime.now() - timedelta(days=window_days)
    count = sum(
        1 for t in all_trades
        if t["ticker"] == ticker
        and t["trade_type"] == "purchase"
        and _parse_date(t["transaction_date"]) >= cutoff
    )
    return round(1.0 + 0.5 * max(0, count - 1), 2)


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        return datetime.min


def score_trade(trade: dict, all_trades: list[dict]) -> dict:
    politician_w = _politician_weight(trade["representative"])
    amount_w = _amount_weight(trade["amount_range"])
    recency_w = _recency_weight(trade["transaction_date"])
    cluster_b = _cluster_bonus(trade["ticker"], all_trades) if trade["trade_type"] == "purchase" else 1.0

    raw_score = politician_w * amount_w * recency_w * cluster_b

    # sales are negative signals
    if trade["trade_type"] in ("sale_full", "sale_partial", "sale"):
        raw_score *= -1

    return {
        **trade,
        "score": round(raw_score, 3),
        "score_components": {
            "politician": politician_w,
            "amount": amount_w,
            "recency": recency_w,
            "cluster": cluster_b,
        },
        "signal": "BUY" if raw_score > 0.5 else ("SELL" if raw_score < -0.5 else "NEUTRAL"),
    }


def score_all(trades: list[dict]) -> list[dict]:
    scored = [score_trade(t, trades) for t in trades if t["ticker"]]
    return sorted(scored, key=lambda x: abs(x["score"]), reverse=True)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from src.ingestion.congress import get_recent_trades

    trades = get_recent_trades(days=90)
    scored = score_all(trades)

    print(f"Top 10 signals from {len(scored)} trades:\n")
    for s in scored[:10]:
        print(
            f"[{s['transaction_date']}] {s['signal']:7s} {s['ticker']:6s} "
            f"score={s['score']:+.2f}  {s['representative']}  {s['amount_range']}"
        )
