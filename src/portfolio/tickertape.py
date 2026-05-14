"""
Tickertape US portfolio reader.
Reads live holdings from tickertape.in via page text parsing.
Falls back to cached JSON if browser unavailable.
"""

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "data", "portfolio", "tickertape_us.json",
)
_CACHE_PATH = os.path.normpath(_CACHE_PATH)

_SOURCE_URL = "tickertape.in/portfolio/us-stocks"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _clean_number(s: str) -> Optional[float]:
    """Strip currency symbols, commas, percent signs and convert to float."""
    s = s.strip().lstrip("$").replace(",", "").rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def parse_portfolio_text(text: str) -> List[Dict]:
    """
    Parse raw text extracted from tickertape.in/portfolio/us-stocks.

    The page text repeats a block per holding that looks like:

        Alphabet Inc Class A
        GOOGL
        $402.68
        3.95%

        0.3155

        $338.32

        $106.75

        $127.05

        28.43%

        +$20.3 (19.02%)

    Returns a list of dicts with keys:
        ticker, name, qty, avg_price, current_price,
        invested, current_value, weight_pct, pnl_pct
    """
    # Tokenise: split by newline, strip, drop blank lines
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    holdings: List[Dict] = []
    i = 0
    n = len(lines)

    # Ticker tokens are all-uppercase, 1-5 chars, optionally with a trailing
    # exchange suffix separated by a dot.
    _TICKER_RE = re.compile(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$')

    # Pattern for "+$20.3 (19.02%)" or "-$20.3 (19.02%)"
    _PNL_LINE_RE = re.compile(
        r'^[+\-]\$[\d,]+\.?\d*\s+\(([+\-]?\d+\.?\d*)%\)$'
    )

    while i < n:
        # Look ahead for a ticker on the next line after a name line
        if i + 1 < n and _TICKER_RE.match(lines[i + 1]):
            name = lines[i]
            ticker = lines[i + 1]
            i += 2

            # Next block: current_price, day_change%, blank(s), qty, blank(s),
            #             avg_price, blank(s), invested, blank(s),
            #             current_value, blank(s), weight_pct, blank(s),
            #             pnl line
            # Collect the next ~20 tokens and extract by pattern
            segment = lines[i: i + 20]
            j = 0
            current_price: Optional[float] = None
            qty: Optional[float] = None
            avg_price: Optional[float] = None
            invested: Optional[float] = None
            current_value: Optional[float] = None
            weight_pct: Optional[float] = None
            pnl_pct: Optional[float] = None

            dollar_values: List[float] = []
            pct_values: List[float] = []

            while j < len(segment):
                tok = segment[j]

                # P&L line: "+$20.3 (19.02%)"
                m = _PNL_LINE_RE.match(tok)
                if m:
                    pnl_pct = float(m.group(1))
                    j += 1
                    break

                # Dollar amount
                if tok.startswith("$") or tok.startswith("-$") or tok.startswith("+$"):
                    val = _clean_number(tok.lstrip("+-"))
                    if val is not None:
                        dollar_values.append(val)

                # Percentage (not day change — those have +/- prefix usually)
                elif tok.endswith("%") and not tok.startswith(("+", "-")):
                    val = _clean_number(tok)
                    if val is not None:
                        pct_values.append(val)

                # Plain float (qty)
                else:
                    try:
                        val = float(tok)
                        if qty is None and 0 < val < 10_000:
                            qty = val
                    except ValueError:
                        pass

                j += 1

            # Assign dollar values in order: current_price, avg_price,
            # invested, current_value
            if len(dollar_values) >= 1:
                current_price = dollar_values[0]
            if len(dollar_values) >= 2:
                avg_price = dollar_values[1]
            if len(dollar_values) >= 3:
                invested = dollar_values[2]
            if len(dollar_values) >= 4:
                current_value = dollar_values[3]

            # First non-day-change pct is weight
            if pct_values:
                weight_pct = pct_values[0]

            i += j

            holding = {
                "ticker": ticker,
                "name": name,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "invested": invested,
                "current_value": current_value,
                "weight_pct": weight_pct,
                "pnl_pct": pnl_pct,
            }
            holdings.append(holding)
        else:
            i += 1

    return holdings


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def load_portfolio(max_age_hours: float = 4.0) -> List[Dict]:
    """
    Load holdings from the local JSON cache.

    If the file is missing or older than *max_age_hours*, logs a warning
    but still returns whatever is cached (or an empty list if missing).

    Returns
    -------
    list[dict]
        Holdings, potentially empty.
    """
    if not os.path.exists(_CACHE_PATH):
        logger.warning("Cache not found: %s", _CACHE_PATH)
        return []

    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cannot read cache %s: %s", _CACHE_PATH, exc)
        return []

    # Age check
    fetched_at_str = data.get("fetched_at")
    if fetched_at_str:
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            age_hours = (
                datetime.now(timezone.utc) - fetched_at
            ).total_seconds() / 3600
            if age_hours > max_age_hours:
                logger.warning(
                    "Cache is %.1f hours old (threshold %.1f h) — "
                    "consider refreshing via browser.",
                    age_hours,
                    max_age_hours,
                )
        except ValueError:
            logger.warning("Cannot parse fetched_at: %r", fetched_at_str)

    return data.get("holdings", [])


def save_portfolio(holdings: List[Dict]) -> None:
    """
    Persist holdings to the JSON cache atomically.

    Computes totals and writes metadata (fetched_at, source,
    total_invested, total_current_value).
    """
    total_invested = sum(
        h.get("invested") or 0.0 for h in holdings
    )
    total_current_value = sum(
        h.get("current_value") or 0.0 for h in holdings
    )

    payload = {
        "source": _SOURCE_URL,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "holdings": holdings,
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current_value, 2),
    }

    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)

    dir_ = os.path.dirname(_CACHE_PATH)
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, _CACHE_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Saved %d holdings to %s", len(holdings), _CACHE_PATH)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def get_portfolio_summary(holdings: List[Dict]) -> Dict:
    """
    Compute aggregate statistics across all holdings.

    Returns
    -------
    dict with keys:
        total_invested, total_current_value, total_pnl_pct,
        winners, losers, biggest_winner, biggest_loser
    """
    if not holdings:
        return {
            "total_invested": 0.0,
            "total_current_value": 0.0,
            "total_pnl_pct": 0.0,
            "winners": 0,
            "losers": 0,
            "biggest_winner": None,
            "biggest_loser": None,
        }

    total_invested = sum(h.get("invested") or 0.0 for h in holdings)
    total_current_value = sum(h.get("current_value") or 0.0 for h in holdings)

    if total_invested > 0:
        total_pnl_pct = (total_current_value - total_invested) / total_invested * 100
    else:
        total_pnl_pct = 0.0

    winners = [h for h in holdings if (h.get("pnl_pct") or 0.0) > 0]
    losers  = [h for h in holdings if (h.get("pnl_pct") or 0.0) < 0]

    biggest_winner = (
        max(winners, key=lambda h: h.get("pnl_pct") or 0.0)
        if winners else None
    )
    biggest_loser = (
        min(losers, key=lambda h: h.get("pnl_pct") or 0.0)
        if losers else None
    )

    return {
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current_value, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "winners": len(winners),
        "losers": len(losers),
        "biggest_winner": biggest_winner,
        "biggest_loser": biggest_loser,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _pnl_color(pnl: Optional[float]) -> str:
    """Return 'green' or 'red' based on sign."""
    if pnl is None:
        return "white"
    return "green" if pnl >= 0 else "red"


def _fmt(val: Optional[float], prefix: str = "", suffix: str = "") -> str:
    if val is None:
        return "-"
    return f"{prefix}{val:,.2f}{suffix}"


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
        _RICH = True
    except ImportError:
        _RICH = False

    holdings = load_portfolio()

    if not holdings:
        print("No holdings found in cache.")
        sys.exit(0)

    summary = get_portfolio_summary(holdings)

    if _RICH:
        console = Console()

        table = Table(
            title="[bold]Tickertape US Portfolio[/bold]",
            box=box.SIMPLE_HEAVY,
            show_lines=True,
            highlight=True,
        )
        table.add_column("Ticker",        style="bold cyan",   justify="left",  min_width=6)
        table.add_column("Name",          style="white",        justify="left",  min_width=28)
        table.add_column("Qty",           style="white",        justify="right", min_width=8)
        table.add_column("Avg $",         style="white",        justify="right", min_width=8)
        table.add_column("Price $",       style="white",        justify="right", min_width=8)
        table.add_column("Invested $",    style="white",        justify="right", min_width=10)
        table.add_column("Value $",       style="white",        justify="right", min_width=10)
        table.add_column("P&L %",         justify="right",      min_width=8)
        table.add_column("Weight %",      style="white",        justify="right", min_width=9)

        for h in holdings:
            pnl = h.get("pnl_pct")
            color = _pnl_color(pnl)
            pnl_str = (
                f"[{color}]{pnl:+.2f}%[/{color}]"
                if pnl is not None else "-"
            )
            table.add_row(
                h.get("ticker", "-"),
                h.get("name", "-"),
                _fmt(h.get("qty"), suffix=""),
                _fmt(h.get("avg_price"), prefix="$"),
                _fmt(h.get("current_price"), prefix="$"),
                _fmt(h.get("invested"), prefix="$"),
                _fmt(h.get("current_value"), prefix="$"),
                pnl_str,
                _fmt(h.get("weight_pct"), suffix="%"),
            )

        console.print(table)

        # Summary panel
        console.print()
        console.print(f"  Invested :  [white]${summary['total_invested']:,.2f}[/white]")
        console.print(f"  Value    :  [white]${summary['total_current_value']:,.2f}[/white]")
        total_pnl = summary["total_pnl_pct"]
        pnl_color = "green" if total_pnl >= 0 else "red"
        console.print(f"  Total P&L:  [{pnl_color}]{total_pnl:+.2f}%[/{pnl_color}]")
        console.print(
            f"  Winners  :  [green]{summary['winners']}[/green]   "
            f"Losers: [red]{summary['losers']}[/red]"
        )
        if summary["biggest_winner"]:
            bw = summary["biggest_winner"]
            console.print(
                f"  Best     :  [green]{bw['ticker']} "
                f"({bw.get('pnl_pct', 0):+.2f}%)[/green]"
            )
        if summary["biggest_loser"]:
            bl = summary["biggest_loser"]
            console.print(
                f"  Worst    :  [red]{bl['ticker']} "
                f"({bl.get('pnl_pct', 0):+.2f}%)[/red]"
            )
        console.print()

    else:
        # Plain-text fallback
        header = f"{'Ticker':<8} {'Name':<30} {'Qty':>8} {'Avg$':>8} {'Price$':>8} {'P&L%':>8} {'Wt%':>7}"
        print(header)
        print("-" * len(header))
        for h in holdings:
            print(
                f"{h.get('ticker',''):8} "
                f"{h.get('name',''):30} "
                f"{h.get('qty', 0):8.4f} "
                f"{h.get('avg_price', 0):8.2f} "
                f"{h.get('current_price', 0):8.2f} "
                f"{h.get('pnl_pct', 0):+8.2f} "
                f"{h.get('weight_pct', 0):7.2f}%"
            )
        print()
        print(f"Invested: ${summary['total_invested']:,.2f}  "
              f"Value: ${summary['total_current_value']:,.2f}  "
              f"P&L: {summary['total_pnl_pct']:+.2f}%")
