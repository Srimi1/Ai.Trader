"""
Portfolio analyzer — cross-references Tickertape holdings against
congressional signals and asks Claude Sonnet for portfolio advice.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parents[2]))

logger = logging.getLogger(__name__)

# ── portfolio JSON path (written by tickertape.py) ────────────────────────────
_PORTFOLIO_PATH = Path(__file__).parents[2] / "data" / "portfolio" / "tickertape_us.json"

# ── thresholds ────────────────────────────────────────────────────────────────
_DANGER_SCORE_THRESHOLD    = -0.4   # congressional SELL signal
_LOSS_PCT_THRESHOLD        = -5.0   # P&L cutoff for "losses" bucket
_OPPORTUNITY_SCORE_MIN     = 0.5    # min BUY score to surface as opportunity
_GEO_RISK_THRESHOLD        = 4.0    # geo risk score that flags a holding


# ── load portfolio ────────────────────────────────────────────────────────────

def load_portfolio() -> List[Dict[str, Any]]:
    """
    Load holdings from the local Tickertape JSON snapshot.
    Returns list of holding dicts.  Raises FileNotFoundError with a
    friendly message if the file doesn't exist yet.
    """
    if not _PORTFOLIO_PATH.exists():
        raise FileNotFoundError(
            "Portfolio data not found.\n"
            "Run:  python src/portfolio/tickertape.py first"
        )
    with open(_PORTFOLIO_PATH) as f:
        data = json.load(f)
    return data.get("holdings", [])


# ── core analysis ─────────────────────────────────────────────────────────────

def analyze_portfolio(days: int = 90) -> Dict[str, Any]:
    """
    Cross-reference portfolio holdings against live congressional signals.

    Returns a dict with keys:
        holdings, dangers, losses, opportunities, geo_risks,
        safe_holds, signals_in_portfolio
    """
    # -- imports kept inside function so CLI --no-claude works without .env
    from src.ingestion.congress import get_recent_trades
    from src.analysis.signals import score_all
    from src.analysis.geo_context import get_geo_risk

    # 1. portfolio
    holdings = load_portfolio()
    held_tickers = {h["ticker"].upper() for h in holdings}
    holding_map: Dict[str, Dict] = {h["ticker"].upper(): h for h in holdings}

    # 2. congressional signals
    raw_trades = get_recent_trades(days=days)
    scored = score_all(raw_trades)

    # 3. signals that overlap with portfolio
    signals_in_portfolio: List[Dict] = []
    for sig in scored:
        ticker = (sig.get("ticker") or "").upper()
        if ticker in held_tickers:
            signals_in_portfolio.append({**sig, "holding": holding_map[ticker]})

    # 4. categorize holdings
    dangers: List[Dict] = []
    losses: List[Dict] = []
    safe_holds: List[Dict] = []

    # build a quick lookup: ticker → worst score among signals in portfolio
    worst_score: Dict[str, float] = {}
    for sig in signals_in_portfolio:
        t = (sig.get("ticker") or "").upper()
        worst_score[t] = min(worst_score.get(t, 0.0), sig.get("score", 0.0))

    for h in holdings:
        t = h["ticker"].upper()
        pnl = h.get("pnl_pct", 0.0)
        sig_score = worst_score.get(t, 0.0)

        if sig_score < _DANGER_SCORE_THRESHOLD:
            dangers.append({**h, "signal_score": sig_score})
        elif pnl < _LOSS_PCT_THRESHOLD:
            losses.append(h)
        else:
            safe_holds.append(h)

    # 5. opportunities: top BUY signals NOT already held
    opportunities: List[Dict] = []
    seen_opp: set = set()
    for sig in scored:
        ticker = (sig.get("ticker") or "").upper()
        if (
            ticker
            and ticker not in held_tickers
            and ticker not in seen_opp
            and sig.get("score", 0.0) > _OPPORTUNITY_SCORE_MIN
        ):
            opportunities.append(sig)
            seen_opp.add(ticker)
        if len(opportunities) >= 5:
            break

    # 6. geo risks among holdings
    geo_risks: List[Dict] = []
    for h in holdings:
        t = h["ticker"].upper()
        geo = get_geo_risk(t)
        if geo.get("risk_score", 0.0) >= _GEO_RISK_THRESHOLD:
            geo_risks.append({**h, "geo": geo})

    return {
        "holdings": holdings,
        "dangers": dangers,
        "losses": losses,
        "opportunities": opportunities,
        "geo_risks": geo_risks,
        "safe_holds": safe_holds,
        "signals_in_portfolio": signals_in_portfolio,
    }


# ── Claude review ─────────────────────────────────────────────────────────────

def get_claude_portfolio_review(analysis: Dict[str, Any]) -> str:
    """
    Build a portfolio summary prompt and send it to claude-sonnet-4-6.
    Returns the raw response text.
    """
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)

    holdings = analysis["holdings"]
    total_value = sum(h.get("current_value", 0.0) for h in holdings)
    total_invested = sum(h.get("invested", 0.0) for h in holdings)
    overall_pnl_pct = (
        round((total_value - total_invested) / total_invested * 100, 2)
        if total_invested else 0.0
    )

    # holdings table
    holdings_lines = ["Ticker | Invested | Value | P&L%"]
    for h in holdings:
        holdings_lines.append(
            f"{h['ticker']:5s} | ${h.get('invested', 0):.2f} | "
            f"${h.get('current_value', 0):.2f} | {h.get('pnl_pct', 0):+.1f}%"
        )

    # dangers block
    danger_lines = []
    for d in analysis["dangers"]:
        danger_lines.append(
            f"  {d['ticker']}: signal score {d['signal_score']:+.3f} "
            f"(P&L {d.get('pnl_pct', 0):+.1f}%)"
        )

    # losses block
    loss_lines = [
        f"  {h['ticker']}: {h.get('pnl_pct', 0):+.1f}%"
        for h in analysis["losses"]
    ]

    # opportunities block
    opp_lines = [
        f"  {s['ticker']}: score {s.get('score', 0):+.3f}  "
        f"({s.get('representative', 'Unknown')} — {s.get('trade_type', '?')})"
        for s in analysis["opportunities"]
    ]

    # geo risks
    geo_lines = [
        f"  {g['ticker']}: geo risk {g['geo']['risk_score']}/10 "
        f"({g['geo']['risk_label']}) — {g['geo']['sector_note'] or g['geo']['country_note']}"
        for g in analysis["geo_risks"]
    ]

    # signals in portfolio
    sig_lines = [
        f"  {s['ticker']}: signal={s.get('signal', '?')} "
        f"score={s.get('score', 0):+.3f}  {s.get('representative', 'Unknown')}"
        for s in analysis["signals_in_portfolio"]
    ]

    prompt = f"""Portfolio Summary (retail investor, US stocks, Tickertape):

Total invested: ${total_invested:.2f}
Current value:  ${total_value:.2f}
Overall P&L:    {overall_pnl_pct:+.2f}%

Holdings:
{chr(10).join(holdings_lines)}

Congressional SELL Signals in Portfolio (danger):
{chr(10).join(danger_lines) or '  None'}

Holdings in Loss (>-5%):
{chr(10).join(loss_lines) or '  None'}

Top Congressional BUY Opportunities (not held):
{chr(10).join(opp_lines) or '  None'}

Geopolitical Risk Flags:
{chr(10).join(geo_lines) or '  None'}

All Congressional Signals Touching Portfolio:
{chr(10).join(sig_lines) or '  None'}

Please review this portfolio and provide structured advice in this exact format:

PORTFOLIO HEALTH: [GOOD | CAUTION | DANGER]
TOTAL VALUE: ${total_value:.2f} | P&L: {overall_pnl_pct:+.2f}%

ACTIONS:
TICKER | ACTION | REASON

SUMMARY: 2-3 sentences of plain-English advice."""

    system = (
        "You are a portfolio advisor reviewing congressional signal intelligence "
        "against a retail investor's US stock holdings."
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        timeout=45.0,
    )

    return message.content[0].text if message.content else "(no response)"


# ── rich console output ───────────────────────────────────────────────────────

def print_analysis(analysis: Dict[str, Any], brief: bool = False) -> None:
    """Render analysis to the console with color-coded Rich tables."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    holdings = analysis["holdings"]
    total_value = sum(h.get("current_value", 0.0) for h in holdings)
    total_invested = sum(h.get("invested", 0.0) for h in holdings)
    overall_pnl = total_value - total_invested
    overall_pnl_pct = (overall_pnl / total_invested * 100) if total_invested else 0.0

    console.rule("[bold cyan]Portfolio Analyzer — Congressional Signal Cross-Reference[/bold cyan]")
    console.print(
        f"  Total Invested: [white]${total_invested:.2f}[/white]  "
        f"Current Value: [white]${total_value:.2f}[/white]  "
        f"P&L: [{'green' if overall_pnl >= 0 else 'red'}]{overall_pnl:+.2f} ({overall_pnl_pct:+.1f}%)[/{'green' if overall_pnl >= 0 else 'red'}]"
    )
    console.print()

    if not brief:
        # Full holdings table
        t = Table(title="All Holdings", box=box.SIMPLE_HEAVY, show_header=True)
        t.add_column("Ticker", style="bold")
        t.add_column("Name", style="dim")
        t.add_column("Invested", justify="right")
        t.add_column("Value", justify="right")
        t.add_column("P&L %", justify="right")
        t.add_column("Weight", justify="right")

        for h in holdings:
            pnl = h.get("pnl_pct", 0.0)
            color = "green" if pnl >= 0 else "red"
            t.add_row(
                h["ticker"],
                h.get("name", ""),
                f"${h.get('invested', 0):.2f}",
                f"${h.get('current_value', 0):.2f}",
                f"[{color}]{pnl:+.1f}%[/{color}]",
                f"{h.get('weight_pct', 0):.1f}%",
            )
        console.print(t)

    # Dangers
    if analysis["dangers"]:
        t = Table(title="[bold red]DANGER — Congressional SELL Signals in Portfolio[/bold red]", box=box.SIMPLE_HEAVY)
        t.add_column("Ticker", style="bold red")
        t.add_column("Signal Score", justify="right")
        t.add_column("P&L %", justify="right")
        t.add_column("Value", justify="right")
        for d in analysis["dangers"]:
            pnl = d.get("pnl_pct", 0.0)
            t.add_row(
                d["ticker"],
                f"[red]{d['signal_score']:+.3f}[/red]",
                f"[{'green' if pnl >= 0 else 'red'}]{pnl:+.1f}%[/{'green' if pnl >= 0 else 'red'}]",
                f"${d.get('current_value', 0):.2f}",
            )
        console.print(t)
    else:
        console.print("[green]  No congressional SELL signals in portfolio.[/green]")

    # Losses
    if analysis["losses"]:
        t = Table(title="[yellow]Underperformers (P&L < -5%)[/yellow]", box=box.SIMPLE_HEAVY)
        t.add_column("Ticker", style="bold")
        t.add_column("P&L %", justify="right")
        t.add_column("Invested", justify="right")
        t.add_column("Value", justify="right")
        for h in analysis["losses"]:
            pnl = h.get("pnl_pct", 0.0)
            t.add_row(
                h["ticker"],
                f"[red]{pnl:+.1f}%[/red]",
                f"${h.get('invested', 0):.2f}",
                f"${h.get('current_value', 0):.2f}",
            )
        console.print(t)
    else:
        console.print("[green]  No holdings below -5% P&L threshold.[/green]")

    # Opportunities
    if analysis["opportunities"]:
        t = Table(title="[bold green]Opportunities — Top BUY Signals (not held)[/bold green]", box=box.SIMPLE_HEAVY)
        t.add_column("Ticker", style="bold green")
        t.add_column("Score", justify="right")
        t.add_column("Politician")
        t.add_column("Trade Type")
        t.add_column("Amount")
        for s in analysis["opportunities"]:
            t.add_row(
                s["ticker"],
                f"[green]{s.get('score', 0):+.3f}[/green]",
                s.get("representative", "Unknown"),
                s.get("trade_type", "?"),
                s.get("amount_range", ""),
            )
        console.print(t)
    else:
        console.print("[dim]  No high-conviction BUY opportunities outside current holdings.[/dim]")

    if not brief:
        # Geo risks
        if analysis["geo_risks"]:
            t = Table(title="[bold yellow]Geopolitical Risk Flags[/bold yellow]", box=box.SIMPLE_HEAVY)
            t.add_column("Ticker", style="bold")
            t.add_column("Risk Score", justify="right")
            t.add_column("Label")
            t.add_column("Note")
            for g in analysis["geo_risks"]:
                geo = g["geo"]
                score = geo["risk_score"]
                color = "red" if score >= 7 else "yellow"
                t.add_row(
                    g["ticker"],
                    f"[{color}]{score}/10[/{color}]",
                    geo["risk_label"],
                    geo.get("sector_note") or geo.get("country_note", ""),
                )
            console.print(t)

        # Signals in portfolio
        if analysis["signals_in_portfolio"]:
            t = Table(title="Congressional Signals Touching Portfolio", box=box.SIMPLE_HEAVY)
            t.add_column("Ticker", style="bold")
            t.add_column("Signal")
            t.add_column("Score", justify="right")
            t.add_column("Politician")
            t.add_column("Date")
            t.add_column("Amount")
            for s in analysis["signals_in_portfolio"]:
                sig_label = s.get("signal", "NEUTRAL")
                color = "green" if sig_label == "BUY" else "red" if sig_label == "SELL" else "dim"
                t.add_row(
                    s["ticker"],
                    f"[{color}]{sig_label}[/{color}]",
                    f"{s.get('score', 0):+.3f}",
                    s.get("representative", "Unknown"),
                    s.get("transaction_date", "")[:10],
                    s.get("amount_range", ""),
                )
            console.print(t)
        else:
            console.print("[dim]  No congressional signals matched current holdings.[/dim]")

        # Safe holds
        if analysis["safe_holds"]:
            safe_tickers = ", ".join(h["ticker"] for h in analysis["safe_holds"])
            console.print(f"\n[green]Safe holds (no danger signal, positive P&L):[/green] {safe_tickers}")

    console.print()


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cross-reference portfolio holdings against congressional signals."
    )
    parser.add_argument("--days",     type=int, default=90,
                        help="Congressional trade lookback window in days (default: 90)")
    parser.add_argument("--no-claude", action="store_true",
                        help="Skip Claude call, show raw analysis only")
    parser.add_argument("--brief",    action="store_true",
                        help="Only show dangers + opportunities")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    try:
        analysis = analyze_portfolio(days=args.days)
    except FileNotFoundError as exc:
        print(str(exc))
        sys.exit(1)

    print_analysis(analysis, brief=args.brief)

    if not args.no_claude:
        from rich.console import Console

        console = Console()
        console.rule("[bold cyan]Claude Portfolio Review[/bold cyan]")
        try:
            review = get_claude_portfolio_review(analysis)
            console.print(review)
        except EnvironmentError as exc:
            console.print(f"[red]Claude unavailable:[/red] {exc}")
        except Exception as exc:
            console.print(f"[red]Claude call failed:[/red] {exc}")
