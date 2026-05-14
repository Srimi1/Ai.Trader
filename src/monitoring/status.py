"""
Portfolio status monitor for AI.Trader paper trading.

Shows: open positions, account value, P&L summary, recent signals.

Usage:
  python src/monitoring/status.py
  python src/monitoring/status.py --json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from rich.console import Console
from rich.table import Table

from src.portfolio.journal import Journal

console = Console()


def print_status(as_json: bool = False) -> None:
    j = Journal()
    summary = j.summary()
    open_trades = j.get_open_trades()

    # Try to fetch live P&L from Alpaca (if keys configured)
    account = None
    positions = {}
    try:
        from src.execution.alpaca_broker import get_account, get_positions
        account = get_account()
        positions = get_positions()
    except Exception:
        pass

    if as_json:
        print(json.dumps({
            "summary": summary,
            "account": account,
            "open_trades": open_trades,
        }, indent=2))
        return

    console.print("\n[bold cyan]AI.Trader — Portfolio Status[/bold cyan]\n")

    # Account summary
    if account:
        acct_table = Table(title="Alpaca Paper Account", show_lines=False)
        acct_table.add_column("Metric", style="bold")
        acct_table.add_column("Value", justify="right")
        acct_table.add_row("Portfolio Value", f"${account['portfolio_value']:,.2f}")
        acct_table.add_row("Cash", f"${account['cash']:,.2f}")
        acct_table.add_row("Buying Power", f"${account['buying_power']:,.2f}")
        acct_table.add_row("Day Trades", str(account['daytrade_count']))
        console.print(acct_table)
        console.print()

    # Open positions (from Alpaca)
    if positions:
        pos_table = Table(title=f"Open Positions ({len(positions)})", show_lines=True)
        pos_table.add_column("Ticker", style="bold")
        pos_table.add_column("Qty", justify="right")
        pos_table.add_column("Entry", justify="right")
        pos_table.add_column("Current", justify="right")
        pos_table.add_column("P&L %", justify="right")
        pos_table.add_column("Market Value", justify="right")

        for sym, pos in positions.items():
            pnl_color = "green" if pos["unrealized_pnl_pct"] >= 0 else "red"
            pos_table.add_row(
                sym,
                f"{pos['qty']:.0f}",
                f"${pos['avg_entry_price']:.2f}",
                f"${pos['current_price']:.2f}",
                f"[{pnl_color}]{pos['unrealized_pnl_pct']:+.1f}%[/{pnl_color}]",
                f"${pos['market_value']:,.0f}",
            )
        console.print(pos_table)
        console.print()
    elif open_trades:
        console.print(f"[dim]{len(open_trades)} open trade(s) logged (connect Alpaca for live P&L)[/dim]\n")

    # Journal summary
    if summary["closed_trades"]:
        stats_table = Table(title="Trade History (Closed)", show_lines=False)
        stats_table.add_column("Metric", style="bold")
        stats_table.add_column("Value", justify="right")
        stats_table.add_row("Total Signals", str(summary["total_signals"]))
        stats_table.add_row("Closed Trades", str(summary["closed_trades"]))
        stats_table.add_row("Open Positions", str(summary["open_positions"]))
        if summary["win_rate_pct"] is not None:
            wr_color = "green" if summary["win_rate_pct"] >= 55 else "yellow"
            stats_table.add_row("Win Rate", f"[{wr_color}]{summary['win_rate_pct']:.1f}%[/{wr_color}]")
            avg_color = "green" if (summary["avg_pnl_pct"] or 0) >= 0 else "red"
            stats_table.add_row("Avg Trade P&L", f"[{avg_color}]{summary['avg_pnl_pct']:+.2f}%[/{avg_color}]")
            stats_table.add_row("Best Trade", f"[green]{summary['best_trade_pct']:+.2f}%[/green]")
            stats_table.add_row("Worst Trade", f"[red]{summary['worst_trade_pct']:+.2f}%[/red]")
        if summary["avg_hold_days"]:
            stats_table.add_row("Avg Hold", f"{summary['avg_hold_days']:.0f} days")
        console.print(stats_table)
    else:
        console.print("[dim]No closed trades yet. Run with --execute to start paper trading.[/dim]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    print_status(as_json=args.json)
