"""
Daily pipeline runner for AI.Trader paper trading.

Runs automatically at market open (9:35 AM ET) and optionally at close (3:55 PM ET).
Handles market-closed days gracefully, manages position exits by hold_days threshold.

Usage:
  python scripts/daily_run.py                    # score + Claude, no execution
  python scripts/daily_run.py --execute          # paper trade via Alpaca
  python scripts/daily_run.py --close-exits      # close positions past hold_days
  python scripts/daily_run.py --status           # show portfolio status only

Cron setup (edit with: crontab -e):
  # Morning run: 9:35 AM ET Mon-Fri
  35 9 * * 1-5 cd /path/to/AI.Trader && .venv/bin/python scripts/daily_run.py --execute >> data/logs/daily.log 2>&1

  # EOD close review: 3:55 PM ET Mon-Fri
  55 15 * * 1-5 cd /path/to/AI.Trader && .venv/bin/python scripts/daily_run.py --close-exits >> data/logs/daily.log 2>&1
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from rich.console import Console

console = Console()

_LOG_DIR = Path(__file__).parents[1] / "data" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_DIR / f"daily_{datetime.now().strftime('%Y%m%d')}.log"),
    ],
)
logger = logging.getLogger("daily_run")


def _close_expired_positions(hold_days: int = 30) -> None:
    """Close any paper positions that have been held longer than hold_days."""
    try:
        from src.portfolio.journal import Journal
        from src.execution.alpaca_broker import get_positions, close_position, get_current_price

        journal = Journal()
        open_trades = journal.get_open_trades()
        today = datetime.now().date()

        for trade in open_trades:
            entry_date_str = trade.get("entry_date")
            ticker = trade.get("ticker")
            if not entry_date_str or not ticker:
                continue
            try:
                entry_date = datetime.strptime(entry_date_str[:10], "%Y-%m-%d").date()
                days_held = (today - entry_date).days
            except ValueError:
                continue

            if days_held >= hold_days:
                logger.info("Closing expired position: %s held %d days (>= %d)", ticker, days_held, hold_days)
                try:
                    close_position(ticker)
                    exit_price = get_current_price(ticker)
                    if exit_price:
                        journal.close_trade(ticker, exit_price, today.strftime("%Y-%m-%d"))
                        logger.info("Closed %s @ $%.2f", ticker, exit_price)
                except Exception as e:
                    logger.error("Failed to close %s: %s", ticker, e)

    except Exception as e:
        logger.error("_close_expired_positions failed: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI.Trader daily pipeline runner")
    parser.add_argument("--execute", action="store_true", help="Execute paper trades via Alpaca")
    parser.add_argument("--close-exits", action="store_true", help="Close positions past hold_days")
    parser.add_argument("--hold-days", type=int, default=30, help="Max hold days before auto-close")
    parser.add_argument("--days", type=int, default=90, help="Lookback days for congressional trades")
    parser.add_argument("--top", type=int, default=5, help="Max signals to act on per run")
    parser.add_argument("--status", action="store_true", help="Show portfolio status and exit")
    parser.add_argument("--no-email", action="store_true", help="Skip email notifications")
    parser.add_argument("--send-emails", action="store_true", help="Flush pending email queue (run from Claude Code)")
    args = parser.parse_args()

    console.rule(f"[bold cyan]AI.Trader Daily Run — {datetime.now().strftime('%Y-%m-%d %H:%M')}[/bold cyan]")

    # Status-only mode
    if args.status:
        from src.monitoring.status import print_status
        print_status()
        return

    # Close expired positions (end-of-day job)
    if args.close_exits:
        logger.info("Running EOD position close check (hold_days=%d)", args.hold_days)
        _close_expired_positions(hold_days=args.hold_days)
        from src.monitoring.status import print_status
        print_status()
        return

    # Flush pending email queue (call from Claude Code to actually send via Gmail MCP)
    if args.send_emails:
        from src.notifications.email import list_pending
        pending = list_pending()
        if not pending:
            console.print("[dim]No pending email notifications.[/dim]")
        else:
            console.print(f"[cyan]{len(pending)} pending notification(s):[/cyan]")
            for n in pending:
                console.print(f"  → {n['subject']} → {n.get('to','')}")
            console.print("\nCall flush_pending_notifications() then send via Gmail MCP.")
        return

    # Main pipeline
    logger.info("Starting pipeline: execute=%s, days=%d, top=%d", args.execute, args.days, args.top)

    from src.agents.orchestrator import run
    run(
        days=args.days,
        top_n=args.top,
        dry_run=not args.execute,
        execute=args.execute,
        hold_days=args.hold_days,
    )

    # Queue email digest
    if not args.no_email:
        try:
            from src.portfolio.journal import Journal
            from src.notifications.email import send_daily_digest
            j = Journal()
            recent = j.get_recent(limit=10)
            digest_data = [
                {
                    "ticker": r["ticker"],
                    "rec": r["recommendation"],
                    "confidence": r["confidence"] or "",
                    "score": r.get("score") or 0,
                    "politician": r.get("representative") or "",
                    "position_size": r.get("position_size_pct") or "",
                }
                for r in recent if r.get("status") not in ("logged",)
            ]
            if digest_data:
                send_daily_digest(digest_data)
                console.print("[dim]Email digest queued → srijansaanand0@gmail.com[/dim]")
        except Exception as _email_err:
            logger.debug("Email digest failed: %s", _email_err)

    # Print status summary after each run
    console.rule()
    from src.monitoring.status import print_status
    print_status()

    logger.info("Daily run complete.")


if __name__ == "__main__":
    main()
