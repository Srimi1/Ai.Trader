"""Risk guardrails: filter trades that don't meet minimum criteria before sending to decision agent."""
from datetime import datetime


MAX_POSITION_PCT = 5.0
MIN_SIGNAL_SCORE = 0.3
MAX_DISCLOSURE_LAG_DAYS = 45


def _disclosure_lag(trade: dict) -> int:
    try:
        tx_str = trade.get("transaction_date") or ""
        disc_str = trade.get("disclosure_date") or tx_str
        tx = datetime.strptime(tx_str[:10], "%Y-%m-%d")
        disc = datetime.strptime(disc_str[:10], "%Y-%m-%d")
        return (disc - tx).days
    except ValueError:
        return 0


def filter_trades(trades: list[dict]) -> tuple[list[dict], list[dict]]:
    approved, rejected = [], []
    for t in trades:
        reasons = []
        score = abs(t.get("adjusted_score", t.get("score", 0)))
        if score < MIN_SIGNAL_SCORE:
            reasons.append(f"score {score:.2f} < min {MIN_SIGNAL_SCORE}")
        lag = _disclosure_lag(t)
        if lag > MAX_DISCLOSURE_LAG_DAYS:
            reasons.append(f"disclosure lag {lag}d > max {MAX_DISCLOSURE_LAG_DAYS}d")
        if not t.get("ticker"):
            reasons.append("no ticker")

        if reasons:
            rejected.append({**t, "rejected_reasons": reasons})
        else:
            approved.append(t)
    return approved, rejected


def position_size(score: float, max_pct: float = MAX_POSITION_PCT) -> float:
    # scale linearly: score 0.3 → 1%, score 3.0+ → max_pct
    normalized = min(abs(score) / 3.0, 1.0)
    return round(normalized * max_pct, 1)
