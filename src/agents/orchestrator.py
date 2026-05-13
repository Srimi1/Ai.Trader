"""
Main pipeline runner.

Usage:
  python src/agents/orchestrator.py                  # last 90 days, top 5 trades
  python src/agents/orchestrator.py --days 30        # last 30 days
  python src/agents/orchestrator.py --dry-run        # skip Claude call, show scores only
  python src/agents/orchestrator.py --backtest       # run backtest on approved signals
  python src/agents/orchestrator.py --backtest --engine backtrader
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parents[2]))

from src.ingestion.congress import get_recent_trades
from src.analysis.signals import score_all
from src.analysis.sentiment import apply_sentiment
from src.analysis.macro import apply_macro_context
from src.agents.risk_agent import filter_trades
from src.agents.decision_agent import get_recommendation, parse_recommendation
from src.backtesting import (
    VectorBTAdapter,
    BacktraderAdapter,
    PyBrokerAdapter,
    generate_report,
)

console = Console()

ENGINE_MAP = {
    "vectorbt": VectorBTAdapter,
    "backtrader": BacktraderAdapter,
    "pybroker": PyBrokerAdapter,
}


def run(
    days: int = 90,
    top_n: int = 5,
    dry_run: bool = False,
    backtest: bool = False,
    engine_name: str = "vectorbt",
    hold_days: int = 30,
    initial_cash: float = 100_000.0,
) -> None:
    console.print(f"\n[bold cyan]Political Trades AI Agent[/bold cyan] — US Markets\n")

    # 1. Ingest
    console.print("[1/5] Fetching congressional disclosures...")
    trades = get_recent_trades(days=days)
    console.print(f"      {len(trades)} trades in last {days} days")

    # 2. Score
    console.print("[2/5] Scoring signals...")
    scored = score_all(trades)

    # 3. Sentiment
    console.print("[3/5] Fetching news sentiment...")
    enriched = apply_sentiment(scored[:top_n * 3])

    # 4. Macro context (WorldMonitor — VIX + sector momentum)
    console.print("[4/5] Applying WorldMonitor macro context...")
    macro_enriched, macro_snapshot = apply_macro_context(enriched, verbose=True)
    vix = macro_snapshot.get("vix", {})
    if vix.get("current"):
        console.print(f"      VIX={vix['current']:.1f} ({vix.get('change_pct', 0):+.1f}% 20d)")

    # 5. Risk filter
    approved, rejected = filter_trades(macro_enriched)
    console.print(f"      {len(approved)} approved, {len(rejected)} rejected by risk filter")

    top = approved[:top_n]

    if not top:
        console.print("[yellow]No trades passed risk filter.[/yellow]")
        return

    # Summary table
    table = Table(title="Top Signals", show_lines=True)
    table.add_column("Date", style="dim")
    table.add_column("Ticker", style="bold")
    table.add_column("Signal")
    table.add_column("Score", justify="right")
    table.add_column("Macro", justify="right")
    table.add_column("Sentiment")
    table.add_column("Sector")
    table.add_column("Politician")

    for t in top:
        signal_color = "green" if t["final_signal"] == "BUY" else ("red" if t["final_signal"] == "SELL" else "yellow")
        macro_score = t.get("macro_adjusted_score", t.get("adjusted_score", 0))
        sector = t.get("macro_context", {}).get("sector") or "—"
        table.add_row(
            t["transaction_date"][:10],
            t["ticker"],
            f"[{signal_color}]{t['final_signal']}[/{signal_color}]",
            f"{t['adjusted_score']:+.2f}",
            f"{macro_score:+.2f}",
            t["sentiment"]["label"],
            sector,
            t["representative"],
        )
    console.print(table)

    if dry_run:
        console.print("\n[dim]--dry-run: skipping Claude recommendations[/dim]")
        if backtest:
            console.print("[dim]--dry-run: skipping backtest[/dim]")
        return

    # 5. Claude decisions
    console.print("\n[4/4] Getting Claude recommendations...\n")
    for trade in top:
        result = get_recommendation(trade)
        parsed = parse_recommendation(result["raw"])

        rec = parsed.get("RECOMMENDATION", "HOLD")
        confidence = parsed.get("CONFIDENCE", "MEDIUM")
        rec_color = "green" if rec == "BUY" else ("red" if rec == "SELL" else "yellow")

        console.print(f"[bold]{trade['ticker']}[/bold] — [{rec_color}]{rec}[/{rec_color}] ({confidence})")
        console.print(f"  Size: {parsed.get('POSITION_SIZE', 'N/A')}  "
                      f"SL: {parsed.get('STOP_LOSS', 'N/A')}  "
                      f"TP: {parsed.get('TAKE_PROFIT', 'N/A')}")
        if "REASONING" in parsed:
            console.print(f"  Thesis: {parsed['REASONING']}")
        if "RISK_NOTE" in parsed:
            console.print(f"  [yellow]Risk: {parsed['RISK_NOTE']}[/yellow]")
        console.print()

    # 6. Backtest (optional)
    if backtest:
        console.print(f"\n[bold cyan]Running backtest — {engine_name}[/bold cyan]\n")
        engine_cls = ENGINE_MAP.get(engine_name, VectorBTAdapter)
        engine = engine_cls()

        # Use all approved signals for backtest, not just top N
        engine.load_signals(approved, hold_days=hold_days)
        try:
            metrics = engine.run(initial_cash=initial_cash)
        except Exception as e:
            console.print(f"[red]Backtest failed: {e}[/red]")
            return

        # Metrics table
        mt = Table(title="Backtest Results", show_lines=True)
        mt.add_column("Metric", style="bold")
        mt.add_column("Value", justify="right")
        mt.add_row("Total Return", f"{metrics.total_return_pct:+.2f}%")
        mt.add_row("Sharpe Ratio", f"{metrics.sharpe_ratio:.3f}")
        mt.add_row("Max Drawdown", f"{metrics.max_drawdown_pct:.2f}%")
        mt.add_row("Win Rate", f"{metrics.win_rate_pct:.1f}%")
        mt.add_row("Profit Factor", f"{metrics.profit_factor:.3f}")
        mt.add_row("Num Trades", str(metrics.num_trades))
        mt.add_row("Calmar Ratio", f"{metrics.calmar_ratio:.3f}")
        mt.add_row("Alpha", f"{metrics.alpha:.3f}")
        mt.add_row("Beta", f"{metrics.beta:.3f}")
        mt.add_row("SPY Benchmark", f"{metrics.benchmark_return_pct:+.2f}%")
        mt.add_row("Excess Return", f"{metrics.excess_return_pct:+.2f}%")
        console.print(mt)

        # Save report
        report_path = generate_report(
            metrics,
            engine_name=engine_name,
            output_path=f"data/processed/reports/backtest_{engine_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.html",
        )
        console.print(f"\n[dim]Report saved → {report_path}[/dim]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backtest", action="store_true", help="Run backtest on approved signals")
    parser.add_argument("--engine", type=str, default="vectorbt", choices=list(ENGINE_MAP.keys()))
    parser.add_argument("--hold-days", type=int, default=30)
    parser.add_argument("--cash", type=float, default=100_000.0)
    args = parser.parse_args()

    run(
        days=args.days,
        top_n=args.top,
        dry_run=args.dry_run,
        backtest=args.backtest,
        engine_name=args.engine,
        hold_days=args.hold_days,
        initial_cash=args.cash,
    )
