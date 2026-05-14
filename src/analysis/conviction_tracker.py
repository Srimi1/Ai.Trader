"""
Conviction Tracker — long-term 45d+ strategy.
Ranks politicians by historical win rate using current signals as proxy.

Proxy metrics (no historical P&L yet):
  - Cluster score: politicians who cluster-buy correlate with winning trades
  - Amount weight: larger disclosed positions imply higher conviction
  - Recency: active traders have fresher information advantage
"""
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[2]))

from src.ingestion.congress import get_recent_trades
from src.analysis.signals import score_all, CONFIG_PATH, _politician_weight


def _amount_weight_from_range(amount_range: str) -> float:
    """Map amount range string to a numeric weight (higher = bigger bet)."""
    r = amount_range.replace(" - ", "-").replace(" – ", "-")
    if "$1,000,001" in r:
        return 2.0
    if "$500,001" in r:
        return 1.8
    if "$250,001" in r:
        return 1.5
    if "$100,001" in r:
        return 1.3
    if "$50,001" in r:
        return 1.1
    if "$15,001" in r:
        return 0.9
    if "$1,001" in r:
        return 0.6
    return 0.8


def _cluster_bonus_for_trade(ticker: str, all_trades: list, window_days: int = 60) -> float:
    """Return cluster bonus (1.0 + 0.5 per extra buyer) for a ticker."""
    cutoff = datetime.now() - timedelta(days=window_days)
    buyers = set()
    for t in all_trades:
        if t.get("ticker") != ticker or t.get("trade_type") != "purchase":
            continue
        try:
            td = datetime.strptime(t["transaction_date"][:10], "%Y-%m-%d")
        except ValueError:
            continue
        if td >= cutoff:
            buyers.add(t["representative"])
    count = len(buyers)
    return round(1.0 + 0.5 * max(0, count - 1), 2)


def rank_politicians(days: int = 365) -> list:
    """
    Rank politicians by proxy conviction score.

    Conviction score = mean(amount_weight) * mean(cluster_bonus) * politician_weight
    Returns list of dicts sorted descending.
    """
    trades = get_recent_trades(days=days)
    purchases = [t for t in trades if t.get("trade_type") == "purchase"]

    # Group by politician
    by_politician: dict = defaultdict(list)
    for t in purchases:
        name = t.get("representative", "Unknown")
        if name and name != "Unknown":
            by_politician[name].append(t)

    ranked = []
    for name, pol_trades in by_politician.items():
        amount_weights = [_amount_weight_from_range(t.get("amount_range", "")) for t in pol_trades]
        cluster_bonuses = [
            _cluster_bonus_for_trade(t["ticker"], purchases, window_days=days)
            for t in pol_trades
        ]
        avg_amount = round(sum(amount_weights) / len(amount_weights), 3)
        avg_cluster = round(sum(cluster_bonuses) / len(cluster_bonuses), 3)
        pol_weight = _politician_weight(name)

        conviction_score = round(avg_amount * avg_cluster * pol_weight, 4)

        recent_tickers = [
            t["ticker"]
            for t in sorted(pol_trades, key=lambda x: x.get("transaction_date", ""), reverse=True)[:3]
            if t.get("ticker")
        ]

        ranked.append({
            "name": name,
            "committee": _get_committee_label(name),
            "avg_amount_weight": avg_amount,
            "avg_cluster_bonus": avg_cluster,
            "conviction_score": conviction_score,
            "recent_buys": recent_tickers,
            "total_trades": len(pol_trades),
        })

    ranked.sort(key=lambda x: x["conviction_score"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i

    return ranked


def _get_committee_label(name: str) -> str:
    """Return committee role label from config, or 'Unknown'."""
    import json
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        info = config.get("known_active_traders", {}).get(name, {})
        return info.get("committee_name", info.get("committee", "Unknown"))
    except Exception:
        return "Unknown"


def scan(days: int = 365, top_n_politicians: int = 5) -> list:
    """
    Get top-ranked politicians and return their recent BUY signals.

    Returns a flat list of trade signal dicts from the top N politicians.
    """
    pol_ranks = rank_politicians(days=days)
    if not pol_ranks:
        return []

    top_politicians = {p["name"]: p for p in pol_ranks[:top_n_politicians]}

    trades = get_recent_trades(days=days)
    scored = score_all(trades)

    results = []
    for s in scored:
        if s.get("signal") != "BUY":
            continue
        rep = s.get("representative", "")
        if rep not in top_politicians:
            continue

        pol = top_politicians[rep]
        conviction = pol["conviction_score"]
        rank = pol["rank"]

        results.append({
            "ticker": s["ticker"],
            "representative": rep,
            "rank": rank,
            "conviction_score": conviction,
            "signal_score": round(s["score"], 3),
            "trade_date": s.get("transaction_date", "")[:10],
            "action": _long_action(conviction, s["score"]),
            "hold_days": 60,
        })

    # Deduplicate by ticker, keep highest conviction trade
    seen: dict = {}
    for r in results:
        t = r["ticker"]
        if t not in seen or r["conviction_score"] > seen[t]["conviction_score"]:
            seen[t] = r

    final = sorted(seen.values(), key=lambda x: x["conviction_score"], reverse=True)
    return final


def _long_action(conviction: float, score: float) -> str:
    if conviction >= 2.0 and score >= 0.5:
        return "STRONG BUY (long-term)"
    if conviction >= 1.5 or score >= 0.4:
        return "BUY — accumulate"
    return "WATCH"


if __name__ == "__main__":
    print("=== Politician Conviction Rankings ===\n")
    ranked = rank_politicians(days=365)
    if not ranked:
        print("No data available.")
    else:
        header = f"{'Rank':>4}  {'Name':<28} {'Committee':<20} {'Conviction':>10} {'Trades':>7} {'Recent Buys'}"
        print(header)
        print("-" * 100)
        for p in ranked[:10]:
            buys_str = ", ".join(p["recent_buys"]) if p["recent_buys"] else "-"
            print(
                f"{p['rank']:4d}  {p['name']:<28} {p['committee']:<20} "
                f"{p['conviction_score']:10.4f} {p['total_trades']:7d}  {buys_str}"
            )

    print("\n=== Top Politician Trade Signals ===\n")
    signals = scan(days=365, top_n_politicians=5)
    if not signals:
        print("No signals from top politicians.")
    else:
        sig_header = f"{'Ticker':<8} {'Rank':>4} {'Conviction':>10} {'Score':>7} {'Action':<22} {'Politician'}"
        print(sig_header)
        print("-" * 80)
        for s in signals:
            print(
                f"{s['ticker']:<8} {s['rank']:4d} {s['conviction_score']:10.4f} "
                f"{s['signal_score']:7.3f} {s['action']:<22} {s['representative']}"
            )
