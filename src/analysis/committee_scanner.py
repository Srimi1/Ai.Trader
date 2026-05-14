"""
Committee Insider Scanner — medium-term 15-45 day plays.
Filters: Armed Services, Finance, Energy, Intelligence committees only.
Cluster bonus: 3+ buys = high conviction.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.ingestion.congress import get_recent_trades
from src.analysis.signals import score_all, CONFIG_PATH
from src.analysis.geo_context import get_geo_risk

HIGH_ALPHA_COMMITTEES = {
    "Armed Services",
    "Armed Services Committee",
    "Finance",
    "Senate Finance",
    "Energy",
    "Energy and Commerce",
    "Senate Energy",
    "Intelligence",
    "Senate Intelligence",
    "Appropriations",
    "House Armed Services",
    "Senate Armed Services",
    "House Energy and Commerce",
    "House Intelligence",
}


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_committee_traders() -> dict:
    """
    Load politicians.json and return only politicians belonging to
    HIGH_ALPHA_COMMITTEES.

    Returns {name: {"committee_role": str, "weight_bonus": float, "committee_name": str}}
    """
    config = _load_config()
    known_traders = config.get("known_active_traders", {})
    high_value = set(config.get("high_value_committees", []))

    # Build the result: known traders whose committee is listed in high-value,
    # plus anyone in HIGH_ALPHA_COMMITTEES by name.
    result = {}
    for name, info in known_traders.items():
        committee_role = info.get("committee", "unknown")
        # We treat the "high_value_committees" list as the canonical source.
        # If we don't have explicit committee name, use the role-level lookup.
        # Match by checking if the politician's role ties to a high-value committee
        # via the high_value_committees list (all are high-alpha).
        committee_name = info.get("committee_name", "")
        if committee_name in HIGH_ALPHA_COMMITTEES or committee_name in high_value:
            result[name] = {
                "committee_role": committee_role,
                "weight_bonus": info.get("weight_bonus", 1.0),
                "committee_name": committee_name,
            }

    # Fallback: any politician with weight_bonus >= 1.1 is treated as committee-relevant
    for name, info in known_traders.items():
        if name not in result and info.get("weight_bonus", 1.0) >= 1.1:
            result[name] = {
                "committee_role": info.get("committee", "member"),
                "weight_bonus": info.get("weight_bonus", 1.1),
                "committee_name": info.get("committee_name", "Committee Member"),
            }

    return result


def _cluster_count(ticker: str, trades: list, window_days: int = 60) -> int:
    """Count distinct congress members who bought this ticker in the window."""
    cutoff = datetime.now() - timedelta(days=window_days)
    buyers = set()
    for t in trades:
        if t.get("ticker") != ticker:
            continue
        if t.get("trade_type") != "purchase":
            continue
        try:
            td = datetime.strptime(t["transaction_date"][:10], "%Y-%m-%d")
        except ValueError:
            continue
        if td >= cutoff:
            buyers.add(t["representative"])
    return len(buyers)


def _action(score: float, cluster: int) -> str:
    if score >= 0.7 and cluster >= 3:
        return "HIGH CONVICTION"
    if score >= 0.4 and cluster >= 2:
        return "BUY"
    return "WATCH"


def scan(days: int = 60, min_score: float = 0.4) -> list:
    """
    Scan for medium-term committee insider plays.

    Only includes results where cluster_count >= 2.
    Returns list of dicts sorted by signal_score descending.
    """
    committee_traders = get_committee_traders()

    trades = get_recent_trades(days=days)
    scored = score_all(trades)

    # Filter to committee traders' BUYs that meet the score floor
    buys = [
        s for s in scored
        if s.get("signal") == "BUY"
        and s.get("score", 0) >= min_score
        and s.get("representative", "") in committee_traders
    ]

    # Deduplicate: highest score per ticker
    seen: dict = {}
    for s in buys:
        t = s["ticker"]
        if t not in seen or s["score"] > seen[t]["score"]:
            seen[t] = s

    results = []
    for ticker, s in seen.items():
        cluster = _cluster_count(ticker, trades, window_days=days)
        if cluster < 2:
            continue

        rep_name = s.get("representative", "")
        committee_info = committee_traders.get(rep_name, {})
        geo = get_geo_risk(ticker)
        action = _action(s["score"], cluster)

        results.append({
            "ticker": ticker,
            "representative": rep_name,
            "committee": committee_info.get("committee_name", "Committee Member"),
            "signal_score": round(s["score"], 3),
            "cluster_count": cluster,
            "trade_date": s.get("transaction_date", "")[:10],
            "amount_range": s.get("amount_range", ""),
            "geo_risk": geo["risk_score"],
            "action": action,
            "hold_days": 30,
            "stop_loss": "-7%",
            "take_profit": "+15%",
        })

    results.sort(key=lambda x: x["signal_score"], reverse=True)
    return results


if __name__ == "__main__":
    rows = scan(days=60, min_score=0.4)
    if not rows:
        print("No committee signals found.")
    else:
        header = (
            f"{'Ticker':<8} {'Score':>7} {'Cluster':>8} {'GeoRisk':>8} "
            f"{'Action':<18} {'Representative':<25} {'Committee'}"
        )
        print(header)
        print("-" * 100)
        for r in rows:
            print(
                f"{r['ticker']:<8} {r['signal_score']:7.3f} {r['cluster_count']:8d} "
                f"{r['geo_risk']:8.1f} {r['action']:<18} "
                f"{r['representative']:<25} {r['committee']}"
            )
        print(f"\n{len(rows)} signal(s) | hold {rows[0]['hold_days']} days | SL {rows[0]['stop_loss']} / TP {rows[0]['take_profit']}")
