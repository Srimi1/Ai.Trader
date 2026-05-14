"""
Export pipeline signals to JSON for LEAN consumption, then trigger backtest.

Usage:
  python src/portfolio/backtest.py --days 365
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.ingestion.congress import get_recent_trades
from src.analysis.signals import score_all
from src.analysis.sentiment import apply_sentiment
from src.agents.risk_agent import filter_trades


SIGNALS_OUT = Path(__file__).parents[2] / "data" / "processed" / "political_signals.json"
LEAN_PROJECT = Path(__file__).parents[2] / "data" / "lean" / "PoliticalTradesStrategy"


def export_signals(days: int = 365) -> Path:
    trades = get_recent_trades(days=days)
    scored = score_all(trades)
    enriched = apply_sentiment(scored)
    approved, _ = filter_trades(enriched)

    SIGNALS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS_OUT, "w") as f:
        json.dump(approved, f, indent=2, default=str)

    print(f"Exported {len(approved)} signals → {SIGNALS_OUT}")
    return SIGNALS_OUT


def run_backtest() -> None:
    if not LEAN_PROJECT.exists():
        print(f"LEAN project not found at {LEAN_PROJECT}")
        print("Create it first: lean create-project PoliticalTradesStrategy")
        return
    try:
        result = subprocess.run(
            ["lean", "backtest", "PoliticalTradesStrategy"],
            check=True, capture_output=True, text=True,
        )
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"LEAN backtest failed (exit {e.returncode}):\n{e.stderr or ''}")
        raise
    except FileNotFoundError:
        raise FileNotFoundError("'lean' CLI not found — install: pip install lean-cli")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args()

    export_signals(args.days)
    if not args.export_only:
        run_backtest()
