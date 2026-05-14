"""
Fundamental context fetcher for the decision agent.

Pulls income statement, balance sheet, and recent SEC filings from
Financial Datasets API (financialdatasets.ai) for a given ticker.
Used in Phase 4 to give Claude grounded financial evidence before
it makes a BUY/SELL recommendation.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
logger = logging.getLogger(__name__)

_BASE = "https://api.financialdatasets.ai"
_KEY = os.environ.get("FINANCIAL_DATASETS_API_KEY", "")
_HEADERS = {"X-API-KEY": _KEY} if _KEY else {}

if not _KEY:
    logger.warning("FINANCIAL_DATASETS_API_KEY not set — fundamentals fetch will be unauthenticated")


async def _get(path: str, params: dict):
    async with httpx.AsyncClient(base_url=_BASE, headers=_HEADERS, timeout=15.0) as client:
        try:
            r = await client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}


async def _fetch_all(ticker: str):
    """Fetch income, balance sheet, and recent filings in parallel."""
    income_task = _get("/financials/income-statements/", {"ticker": ticker, "period": "ttm", "limit": 2})
    balance_task = _get("/financials/balance-sheets/", {"ticker": ticker, "period": "annual", "limit": 1})
    filings_task = _get("/filings/", {"ticker": ticker, "limit": 5})

    income, balance, filings = await asyncio.gather(income_task, balance_task, filings_task)
    return {"income": income, "balance": balance, "filings": filings}


def _format_income(data: dict) -> str:
    rows = data.get("income_statements", [])
    if not rows:
        return "No income data available."
    r = rows[0]
    lines = [
        f"Period: {r.get('period', 'TTM')} | Revenue: ${r.get('revenue', 0)/1e9:.2f}B",
        f"Gross Profit: ${r.get('gross_profit', 0)/1e9:.2f}B | Op. Income: ${r.get('operating_income', 0)/1e9:.2f}B",
        f"Net Income: ${r.get('net_income', 0)/1e9:.2f}B | EPS: ${r.get('eps_diluted', 0):.2f}",
    ]
    if len(rows) > 1:
        prev = rows[1]
        rev_growth = (r.get("revenue", 0) - prev.get("revenue", 0)) / max(abs(prev.get("revenue", 1)), 1) * 100
        lines.append(f"Revenue YoY growth: {rev_growth:+.1f}%")
    return "\n".join(lines)


def _format_balance(data: dict) -> str:
    rows = data.get("balance_sheets", [])
    if not rows:
        return "No balance sheet data available."
    r = rows[0]
    cash = r.get("cash_and_equivalents", 0) or 0
    debt = r.get("long_term_debt", 0) or 0
    equity = r.get("total_equity", 0) or 0
    return (
        f"Cash: ${cash/1e9:.2f}B | Long-term debt: ${debt/1e9:.2f}B | "
        f"Net cash pos: ${(cash-debt)/1e9:.2f}B | Equity: ${equity/1e9:.2f}B"
    )


def _format_filings(data: dict) -> str:
    rows = data.get("filings", [])
    if not rows:
        return "No recent SEC filings found."
    lines = []
    for f in rows[:5]:
        ftype = f.get("filing_type", "?")
        date = (f.get("filed_at") or f.get("date", ""))[:10]
        desc = f.get("description") or f.get("form_type", "")
        lines.append(f"  [{ftype}] {date} — {desc[:80]}")
    return "\n".join(lines)


def get_fundamentals_context(ticker: str) -> str:
    """
    Synchronous wrapper. Returns a compact multi-line fundamentals block
    ready to inject into a Claude prompt.
    Returns empty string on any failure (non-blocking).
    """
    try:
        raw = asyncio.run(_fetch_all(ticker))
    except Exception as e:
        logger.warning("Fundamentals fetch failed for %s: %s", ticker, e)
        return ""

    if all(isinstance(v, dict) and "error" in v for v in raw.values()):
        logger.warning("All fundamentals endpoints errored for %s", ticker)
        return ""

    block = f"""
Fundamental Data ({ticker}):
  Income Statement:
    {_format_income(raw['income'])}
  Balance Sheet:
    {_format_balance(raw['balance'])}
  Recent SEC Filings:
{_format_filings(raw['filings'])}"""
    return block
