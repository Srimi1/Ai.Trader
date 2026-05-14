"""
GeoConviction Scanner — finds stocks where congressional BUY signals
coincide with rising geopolitical tension in the last 10-15 days.

Logic:
  1. Filter recent congressional BUYs (last 30 days, recency_weight >= 0.50)
  2. For each ticker: check if geo tension is RISING via GDELT keyword search
  3. Score: conviction_score × tension_multiplier
  4. Recommend short-window entry (10-15 days, tighter stop-loss)

Usage:
  python src/analysis/geo_scanner.py
  python src/analysis/geo_scanner.py --days 30 --window 15 --min-score 0.4
"""
import argparse
import asyncio
import json
import logging
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import yfinance as yf
from rich.console import Console
from rich.table import Table

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.ingestion.congress import get_recent_trades
from src.analysis.signals import score_all
from src.analysis.geo_context import get_geo_risk, get_macro_snapshot

console = Console()
logger = logging.getLogger(__name__)

_GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
_CACHE_DIR = Path(__file__).parents[2] / "data" / "cache" / "geo_scanner"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Ticker → geo tension keywords (what to search in GDELT)
_TICKER_TENSION_KEYWORDS = {
    # Semiconductors — Taiwan Strait
    "TSM": "Taiwan Strait military tension",
    "NVDA": "Taiwan Strait semiconductor",
    "AMD": "Taiwan semiconductor supply chain",
    "INTC": "Taiwan chip supply disruption",
    "AVGO": "Taiwan Strait tension",
    "QCOM": "Taiwan semiconductor",
    # Energy — Hormuz/Red Sea
    "XOM": "Strait of Hormuz oil disruption",
    "CVX": "Red Sea oil tanker Hormuz",
    "COP": "Strait of Hormuz oil",
    "BP": "Red Sea oil shipping",
    "SLB": "Middle East energy disruption",
    # Defence — conflict escalation
    "LMT": "military conflict escalation war",
    "RTX": "military conflict weapons",
    "NOC": "defence military conflict",
    "GD": "military escalation",
    "BA": "aerospace defence contract",
    # Shipping — Red Sea / Suez
    "ZIM": "Red Sea shipping Suez Canal",
    # Tech/Cloud — cable / infrastructure
    "AMZN": "undersea cable cloud outage",
    "GOOGL": "internet infrastructure outage",
    "MSFT": "submarine cable disruption",
    # Financials — sanctions
    "GS": "sanctions financial",
    "JPM": "banking sanctions Russia",
    # Default — generic geopolitical search
    "_default": "geopolitical tension market",
}

_SHORT_WINDOW_DAYS = 15  # recommend 10-15 day hold
_RECENCY_THRESHOLD = 0.50  # only recent signals (roughly last 14 days)
_MIN_SIGNAL_SCORE = 0.35


def _cache_key(ticker: str, window_days: int) -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    return f"tension_{ticker}_{window_days}d_{date_str}"


def _cache_get(key: str) -> Optional[dict]:
    p = _CACHE_DIR / f"{key}.json"
    if not p.exists():
        return None
    if (time.time() - p.stat().st_mtime) > 4 * 3600:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _cache_set(key: str, data: dict) -> None:
    try:
        with open(_CACHE_DIR / f"{key}.json", "w") as f:
            json.dump(data, f)
    except Exception:
        pass


async def _gdelt_tension_score(ticker: str, window_days: int = 15) -> dict:
    """
    Query GDELT for ticker-specific geo tension in last window_days.
    Returns {score: 0-10, trend: rising/falling/stable, articles: N, headlines: [...]}
    """
    cache_key = _cache_key(ticker, window_days)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    query = _TICKER_TENSION_KEYWORDS.get(ticker.upper(), _TICKER_TENSION_KEYWORDS["_default"])
    # Add ticker name to make search more specific
    query_recent = query
    query_baseline = query

    async with httpx.AsyncClient() as client:
        try:
            # Recent window (last window_days)
            r_recent = await client.get(_GDELT_BASE, params={
                "query": query_recent,
                "format": "json",
                "mode": "artlist",
                "maxrecords": 15,
                "timespan": f"{window_days}d",
                "sort": "DateDesc",
            }, timeout=15.0)

            # Baseline (prior 30 days for comparison)
            r_baseline = await client.get(_GDELT_BASE, params={
                "query": query_baseline,
                "format": "json",
                "mode": "artlist",
                "maxrecords": 15,
                "timespan": "30d",
                "sort": "DateDesc",
            }, timeout=15.0)

            recent_articles = r_recent.json().get("articles", []) if r_recent.status_code == 200 else []
            baseline_articles = r_baseline.json().get("articles", []) if r_baseline.status_code == 200 else []

        except Exception as e:
            logger.debug("GDELT failed for %s: %s", ticker, e)
            recent_articles = []
            baseline_articles = []

    recent_count = len(recent_articles)
    # Expected baseline rate for comparison window
    baseline_rate = len(baseline_articles) / 30 * window_days if baseline_articles else 0

    # Tension score 0-10
    if baseline_rate == 0:
        raw_score = min(10, recent_count * 1.5)
    else:
        ratio = recent_count / max(baseline_rate, 0.5)
        raw_score = min(10, ratio * 3)

    tension_score = round(raw_score, 1)

    if recent_count > baseline_rate * 1.5 and recent_count >= 3:
        trend = "RISING"
    elif recent_count < baseline_rate * 0.5:
        trend = "FALLING"
    else:
        trend = "STABLE"

    result = {
        "ticker": ticker,
        "tension_score": tension_score,
        "trend": trend,
        "recent_articles": recent_count,
        "headlines": [a.get("title", "")[:80] for a in recent_articles[:3]],
        "query": query,
        "window_days": window_days,
    }
    _cache_set(cache_key, result)
    return result


def _price_momentum(ticker: str, days: int = 15) -> dict:
    """Fetch recent price momentum for context."""
    try:
        hist = yf.Ticker(ticker).history(period=f"{days + 5}d", auto_adjust=True)
        if len(hist) < 2:
            return {"return_pct": None, "volatility_pct": None}
        recent_return = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
        volatility = hist["Close"].pct_change().std() * (252 ** 0.5) * 100
        return {"return_pct": round(recent_return, 2), "volatility_pct": round(volatility, 1)}
    except Exception:
        return {"return_pct": None, "volatility_pct": None}


async def scan(
    days: int = 30,
    window_days: int = 15,
    min_score: float = _MIN_SIGNAL_SCORE,
    min_recency: float = _RECENCY_THRESHOLD,
) -> list:
    """
    Main scanner. Returns list of opportunities sorted by combined score.
    Each item: {ticker, signal, geo_risk, tension, price, combined_score, action}
    """
    # 1. Get congressional BUYs
    trades = get_recent_trades(days=days)
    scored = score_all(trades)
    buys = [
        s for s in scored
        if s.get("signal") == "BUY"
        and abs(s.get("score", 0)) >= min_score
        and s.get("score_components", {}).get("recency", 0) >= min_recency
    ]

    # Deduplicate tickers (keep highest score per ticker)
    seen = {}
    for s in buys:
        t = s["ticker"]
        if t not in seen or s["score"] > seen[t]["score"]:
            seen[t] = s
    unique_buys = list(seen.values())

    if not unique_buys:
        return []

    # 2. Get macro context
    macro = get_macro_snapshot()
    vix = macro.get("vix", {}).get("value", 18)
    vix_mult = macro.get("vix_risk_multiplier", 1.0)

    # 3. Fetch GDELT tension + geo risk per ticker (parallel)
    tension_tasks = [_gdelt_tension_score(s["ticker"], window_days) for s in unique_buys]
    tensions = await asyncio.gather(*tension_tasks)
    tension_map = {t["ticker"]: t for t in tensions}

    # 4. Combine scores
    results = []
    for s in unique_buys:
        ticker = s["ticker"]
        geo = get_geo_risk(ticker)
        tension = tension_map.get(ticker, {"tension_score": 0, "trend": "STABLE", "recent_articles": 0})
        price = _price_momentum(ticker, window_days)

        # Combined score: signal × geo_base × tension_bonus
        # High geo risk + rising tension = amplified signal
        geo_base = 1.0
        if geo["risk_score"] >= 7:
            geo_base = 1.3
        elif geo["risk_score"] >= 4:
            geo_base = 1.15

        tension_bonus = 1.0
        if tension["trend"] == "RISING" and tension["tension_score"] >= 4:
            tension_bonus = 1.4
        elif tension["trend"] == "RISING":
            tension_bonus = 1.2
        elif tension["tension_score"] >= 6:
            tension_bonus = 1.1

        combined = round(s["score"] * geo_base * tension_bonus * vix_mult, 3)

        # Action
        if combined >= 0.8 and tension["trend"] == "RISING":
            action = "STRONG BUY (geo catalyst)"
        elif combined >= 0.6:
            action = "BUY — watch entry"
        elif combined >= 0.4:
            action = "WATCH — signal weak"
        else:
            action = "SKIP"

        # Stop-loss tighter for geo plays (more volatile)
        stop_loss_pct = -6 if geo["risk_score"] >= 5 else -8
        take_profit_pct = 12 if tension["trend"] == "RISING" else 10

        results.append({
            "ticker": ticker,
            "representative": s.get("representative", ""),
            "trade_date": s.get("transaction_date", "")[:10],
            "amount_range": s.get("amount_range", ""),
            "signal_score": round(s["score"], 3),
            "recency_weight": round(s.get("score_components", {}).get("recency", 0), 2),
            "geo_risk_score": geo["risk_score"],
            "geo_risk_label": geo["risk_label"],
            "geo_note": geo.get("sector_note") or geo.get("country_note", ""),
            "tension_score": tension["tension_score"],
            "tension_trend": tension["trend"],
            "tension_articles": tension["recent_articles"],
            "tension_headlines": tension.get("headlines", []),
            "price_return_15d": price.get("return_pct"),
            "volatility_pct": price.get("volatility_pct"),
            "combined_score": combined,
            "action": action,
            "hold_days": _SHORT_WINDOW_DAYS,
            "stop_loss": f"{stop_loss_pct}%",
            "take_profit": f"+{take_profit_pct}%",
            "vix": vix,
        })

    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results


def print_report(results: list, window_days: int = 15) -> None:
    console.print(f"\n[bold cyan]GeoConviction Scanner — {window_days}-Day Window[/bold cyan]")
    console.print(f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')} | Congressional BUYs × Geopolitical Tension[/dim]\n")

    if not results:
        console.print("[yellow]No qualifying signals found.[/yellow]")
        return

    # Main table
    table = Table(title="Top GeoConviction Signals", show_lines=True)
    table.add_column("Ticker", style="bold")
    table.add_column("Action")
    table.add_column("Combined", justify="right")
    table.add_column("Signal", justify="right")
    table.add_column("Geo Risk")
    table.add_column("Tension")
    table.add_column("Trend")
    table.add_column("15d Price")
    table.add_column("Politician")

    for r in results:
        if r["action"] == "SKIP":
            continue
        action_color = (
            "green" if "STRONG" in r["action"]
            else "cyan" if "BUY" in r["action"]
            else "yellow"
        )
        geo_color = "red" if r["geo_risk_score"] >= 7 else "yellow" if r["geo_risk_score"] >= 4 else "dim"
        trend_color = "red" if r["tension_trend"] == "RISING" else "green" if r["tension_trend"] == "FALLING" else "dim"
        price_str = f"{r['price_return_15d']:+.1f}%" if r["price_return_15d"] is not None else "N/A"
        price_color = "green" if (r["price_return_15d"] or 0) >= 0 else "red"

        table.add_row(
            r["ticker"],
            f"[{action_color}]{r['action']}[/{action_color}]",
            f"[bold]{r['combined_score']:+.3f}[/bold]",
            f"{r['signal_score']:+.3f}",
            f"[{geo_color}]{r['geo_risk_score']}/10[/{geo_color}]",
            f"{r['tension_score']:.1f}/10 ({r['tension_articles']} art.)",
            f"[{trend_color}]{r['tension_trend']}[/{trend_color}]",
            f"[{price_color}]{price_str}[/{price_color}]",
            r["representative"][:20],
        )
    console.print(table)

    # Detail blocks for top 3
    console.print()
    for r in [x for x in results if "SKIP" not in x["action"]][:3]:
        console.print(f"[bold]{r['ticker']}[/bold] — {r['action']}")
        console.print(f"  Politician: {r['representative']} | {r['trade_date']} | {r['amount_range']}")
        console.print(f"  Signal: {r['signal_score']:+.3f} | Geo: {r['geo_risk_label']} ({r['geo_risk_score']}/10) | Tension: {r['tension_trend']}")
        if r["geo_note"]:
            console.print(f"  Geo note: {r['geo_note']}")
        if r["tension_headlines"]:
            console.print(f"  Tension headline: {r['tension_headlines'][0][:80]}")
        console.print(f"  [bold]Entry window: {r['hold_days']} days | SL: {r['stop_loss']} | TP: {r['take_profit']}[/bold]")
        console.print()

    # Macro context
    macro = get_macro_snapshot()
    vix = macro.get("vix", {}).get("value", "?")
    regime = macro.get("market_regime", "unknown")
    console.print(f"[dim]VIX: {vix} ({regime}) | All signals use {_SHORT_WINDOW_DAYS}-day hold window[/dim]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GeoConviction Scanner")
    parser.add_argument("--days", type=int, default=30, help="Lookback days for congressional trades")
    parser.add_argument("--window", type=int, default=15, help="Short-window hold days (10-15)")
    parser.add_argument("--min-score", type=float, default=0.35, help="Minimum signal score")
    parser.add_argument("--json-out", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    results = asyncio.run(scan(days=args.days, window_days=args.window, min_score=args.min_score))

    if args.json_out:
        print(json.dumps(results, indent=2))
    else:
        print_report(results, window_days=args.window)
