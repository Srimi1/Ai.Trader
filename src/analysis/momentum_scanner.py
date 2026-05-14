"""
Momentum Scanner — ultra-short 1-5 day bounce plays.
Finds: RSI < 35 + congressional BUY in last 7 days.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import warnings
from typing import Optional

import pandas as pd
import yfinance as yf

from src.ingestion.congress import get_recent_trades
from src.analysis.signals import score_all

warnings.filterwarnings("ignore")


def _compute_rsi(prices: pd.Series, window: int = 14) -> float:
    delta = prices.diff().dropna()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, float("inf"))
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 50.0


def get_rsi(ticker: str) -> Optional[float]:
    """Fetch RSI(14) via yfinance. Returns None on failure."""
    try:
        hist = yf.Ticker(ticker).history(period="60d", auto_adjust=True)
        if hist.empty or len(hist) < 16:
            return None
        return round(_compute_rsi(hist["Close"]), 2)
    except Exception:
        return None


def _price_change_3d(ticker: str) -> Optional[float]:
    """Recent 3-day price change as a percentage."""
    try:
        hist = yf.Ticker(ticker).history(period="10d", auto_adjust=True)
        if len(hist) < 4:
            return None
        start = float(hist["Close"].iloc[-4])
        end = float(hist["Close"].iloc[-1])
        if start == 0:
            return None
        return round((end - start) / start * 100, 2)
    except Exception:
        return None


def _action(rsi: float, score: float) -> str:
    if rsi < 28 and score >= 0.30:
        return "BUY NOW"
    if rsi < 35 and score >= 0.10:
        return "WATCH"
    return "SKIP"


def scan(
    days: int = 7,
    rsi_threshold: float = 35.0,
    min_score: float = 0.10,
) -> list:
    """
    Scan for ultra-short momentum plays.

    Returns list of dicts — one per qualifying ticker.
    """
    trades = get_recent_trades(days=days)
    scored = score_all(trades)

    # Keep only BUYs above the score floor
    buys = [
        s for s in scored
        if s.get("signal") == "BUY" and s.get("score", 0) >= min_score
    ]

    # Deduplicate: highest score per ticker
    seen: dict = {}
    for s in buys:
        t = s["ticker"]
        if t not in seen or s["score"] > seen[t]["score"]:
            seen[t] = s

    results = []
    for ticker, s in seen.items():
        rsi = get_rsi(ticker)
        if rsi is None or rsi >= rsi_threshold:
            continue

        price_change_3d = _price_change_3d(ticker)
        action = _action(rsi, s["score"])

        results.append({
            "ticker": ticker,
            "rsi": rsi,
            "signal_score": round(s["score"], 3),
            "representative": s.get("representative", ""),
            "trade_date": s.get("transaction_date", "")[:10],
            "price_change_3d": price_change_3d if price_change_3d is not None else 0.0,
            "action": action,
            "stop_loss": "-5%",
            "take_profit": "+7%",
            "hold_days": 3,
        })

    results.sort(key=lambda x: x["rsi"])
    return results


if __name__ == "__main__":
    rows = scan(days=7, rsi_threshold=35, min_score=0.10)
    if not rows:
        print("No momentum signals found.")
    else:
        header = f"{'Ticker':<8} {'RSI':>6} {'Score':>7} {'3d%':>7} {'Action':<14} {'Politician'}"
        print(header)
        print("-" * len(header))
        for r in rows:
            print(
                f"{r['ticker']:<8} {r['rsi']:6.1f} {r['signal_score']:7.3f} "
                f"{r['price_change_3d']:+7.2f}% {r['action']:<14} {r['representative']}"
            )
        print(f"\n{len(rows)} signal(s) | SL {rows[0]['stop_loss']} / TP {rows[0]['take_profit']} / hold {rows[0]['hold_days']} days")
