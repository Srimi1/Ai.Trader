"""
Main pipeline runner.

Usage:
  python src/agents/orchestrator.py                         # last 90 days, top 5 trades
  python src/agents/orchestrator.py --days 30               # last 30 days
  python src/agents/orchestrator.py --dry-run               # skip Claude call, show scores only
  python src/agents/orchestrator.py --execute               # paper trade via Alpaca
  python src/agents/orchestrator.py --backtest              # run backtest on approved signals
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
from src.agents.decision_agent import get_recommendation, get_deep_analysis, parse_recommendation
from src.analysis.fundamentals import get_fundamentals_context
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
    execute: bool = False,
    backtest: bool = False,
    engine_name: str = "vectorbt",
    hold_days: int = 30,
    initial_cash: float = 100_000.0,
    deep_analysis: bool = False,
    deep_mode: str = "both",
) -> None:
    console.print("\n[bold cyan]Political Trades AI Agent[/bold cyan] — US Markets\n")

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
        signal_color = "green" if t.get("final_signal") == "BUY" else ("red" if t.get("final_signal") == "SELL" else "yellow")
        adj_score = t.get("adjusted_score", t.get("score", 0.0))
        macro_score = t.get("macro_adjusted_score", adj_score)
        sector = t.get("macro_context", {}).get("sector") or "—"
        sentiment_label = t.get("sentiment", {}).get("label", "N/A")
        table.add_row(
            (t.get("transaction_date") or "")[:10],
            t.get("ticker", "N/A"),
            f"[{signal_color}]{t.get('final_signal', 'N/A')}[/{signal_color}]",
            f"{adj_score:+.2f}",
            f"{macro_score:+.2f}",
            sentiment_label,
            sector,
            t.get("representative", "Unknown"),
        )
    console.print(table)

    if dry_run:
        console.print("\n[dim]--dry-run: skipping Claude recommendations[/dim]")
        if backtest:
            console.print("[dim]--dry-run: skipping backtest[/dim]")
        return

    # 5. Pre-fetch geo + macro context (geo_context.py — Python 3.9, no mcp dep)
    console.print("[5/5] Getting Claude recommendations with geo/macro context...\n")
    try:
        from src.analysis.geo_context import get_geo_risk, get_macro_snapshot
        _macro = get_macro_snapshot()
        _geo_scores = {t.get("ticker", ""): get_geo_risk(t.get("ticker", "")) for t in top}
        _wm_cache = {
            t.get("ticker", ""): {"geo_risk": _geo_scores[t.get("ticker", "")], "market": _macro}
            for t in top
        }
        vix_val = _macro.get("vix", {}).get("value")
        console.print(
            f"      VIX={vix_val} | regime={_macro.get('market_regime', 'unknown')} "
            f"| multiplier={_macro.get('vix_risk_multiplier', 1.0)}"
        )
    except Exception as _wm_err:
        console.print(f"      [dim]Geo/macro context unavailable: {_wm_err}[/dim]")
        _wm_cache = {}

    # Init journal + Alpaca (if executing)
    from src.portfolio.journal import Journal
    journal = Journal()

    alpaca_available = False
    if execute:
        try:
            from src.execution.alpaca_broker import (
                get_account, get_positions, is_market_open,
                place_order, compute_qty, get_current_price,
            )
            if not is_market_open():
                console.print("[yellow]Market closed — signals logged but no orders placed.[/yellow]")
                execute = False
            else:
                acct = get_account()
                alpaca_available = True
                console.print(f"      Alpaca paper account: ${acct['portfolio_value']:,.0f} portfolio | ${acct['cash']:,.0f} cash")
        except EnvironmentError as e:
            console.print(f"[yellow]Alpaca not configured: {e}[/yellow]")
            execute = False
        except Exception as e:
            console.print(f"[red]Alpaca error: {e}[/red]")
            execute = False

    for trade in top:
        ticker = trade.get("ticker", "N/A")
        wm_ctx = _wm_cache.get(ticker, None)

        # Inject geo risk score into trade dict for journal
        if wm_ctx and wm_ctx.get("geo_risk"):
            trade["_geo_risk_score"] = wm_ctx["geo_risk"].get("risk_score")

        # Phase 4: fetch fundamentals + technical signals
        fundamentals = ""
        technicals = ""
        if not dry_run:
            try:
                fundamentals = get_fundamentals_context(ticker)
            except Exception:
                pass
            try:
                from src.ingestion.massive import get_technical_context
                technicals = get_technical_context(ticker)
                if technicals:
                    console.print(f"      [dim]{ticker}: RSI/MACD loaded[/dim]")
            except Exception:
                pass

        result = get_recommendation(trade, wm_context=wm_ctx, fundamentals=fundamentals, technicals=technicals)
        parsed = parse_recommendation(result["raw"])

        rec = parsed.get("RECOMMENDATION", "HOLD")
        confidence = parsed.get("CONFIDENCE", "MEDIUM")
        rec_color = "green" if rec == "BUY" else ("red" if rec == "SELL" else "yellow")

        console.print(f"[bold]{ticker}[/bold] — [{rec_color}]{rec}[/{rec_color}] ({confidence})")
        console.print(f"  Size: {parsed.get('POSITION_SIZE', 'N/A')}  "
                      f"SL: {parsed.get('STOP_LOSS', 'N/A')}  "
                      f"TP: {parsed.get('TAKE_PROFIT', 'N/A')}")
        if "REASONING" in parsed:
            console.print(f"  Thesis: {parsed['REASONING']}")
        if "RISK_NOTE" in parsed:
            console.print(f"  [yellow]Risk: {parsed['RISK_NOTE']}[/yellow]")

        # Phase 4: deep analysis — Lynch Pitch + Munger Invert
        if deep_analysis:
            deep = get_deep_analysis(trade, fundamentals=fundamentals, mode=deep_mode)
            if deep.get("lynch_pitch"):
                console.print(f"\n  [bold green]Lynch Pitch — {ticker}[/bold green]")
                for line in deep["lynch_pitch"].strip().split("\n"):
                    console.print(f"  {line}")
            if deep.get("munger_invert"):
                console.print(f"\n  [bold red]Munger Invert — {ticker}[/bold red]")
                for line in deep["munger_invert"].strip().split("\n"):
                    console.print(f"  {line}")

        # Paper trade execution
        order = None
        if execute and alpaca_available and rec in ("BUY", "SELL"):
            try:
                positions = get_positions()
                pos_str = parsed.get("POSITION_SIZE", "3%").replace("%", "").split()[0]
                pos_pct = float(pos_str) / 100

                if rec == "BUY":
                    if ticker in positions:
                        console.print(f"  [dim]Already hold {ticker} — skipping duplicate[/dim]")
                        journal.log_signal(trade, parsed, source="paper")
                        journal.skip_trade(ticker, "already holding position")
                    else:
                        price = get_current_price(ticker)
                        if price:
                            qty = compute_qty(pos_pct, price)
                            order = place_order(ticker, "buy", qty)
                            order["entry_price"] = price
                            order["entry_date"] = pd.Timestamp.now().strftime("%Y-%m-%d")
                            console.print(f"  [green]BUY order: {qty} shares @ ~${price:.2f}[/green]")
                        else:
                            console.print(f"  [yellow]Could not fetch price for {ticker}[/yellow]")

                elif rec == "SELL":
                    if ticker in positions:
                        pos_qty = positions[ticker]["qty"]
                        order = place_order(ticker, "sell", pos_qty)
                        console.print(f"  [red]SELL order: {pos_qty:.0f} shares[/red]")
                        exit_price = positions[ticker]["current_price"]
                        journal.close_trade(ticker, exit_price)
                    else:
                        console.print(f"  [dim]{ticker}: SELL signal but no open position[/dim]")

            except Exception as _exec_err:
                console.print(f"  [red]Execution error: {_exec_err}[/red]")

        # Log to journal (always)
        source = "paper" if execute and alpaca_available else "dry_run"
        journal.log_signal(trade, parsed, order=order, source=source)

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
    parser.add_argument("--dry-run", action="store_true", help="Score + sentiment only, no Claude/execution")
    parser.add_argument("--execute", action="store_true", help="Execute paper trades via Alpaca")
    parser.add_argument("--backtest", action="store_true", help="Run backtest on approved signals")
    parser.add_argument("--deep-analysis", action="store_true", help="Phase 4: Lynch Pitch + Munger Invert per ticker")
    parser.add_argument("--deep-mode", type=str, default="both", choices=["lynch", "munger", "both"])
    parser.add_argument("--engine", type=str, default="vectorbt", choices=list(ENGINE_MAP.keys()))
    parser.add_argument("--hold-days", type=int, default=30)
    parser.add_argument("--cash", type=float, default=100_000.0)
    args = parser.parse_args()

    run(
        days=args.days,
        top_n=args.top,
        dry_run=args.dry_run,
        execute=args.execute,
        backtest=args.backtest,
        engine_name=args.engine,
        hold_days=args.hold_days,
        initial_cash=args.cash,
        deep_analysis=args.deep_analysis,
        deep_mode=args.deep_mode,
    )
