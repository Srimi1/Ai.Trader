"""MCP server — Financial Datasets API (US equities + SEC filings only)."""
import json
import logging
import os
import sys

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
logger = logging.getLogger("financial-datasets-mcp")

mcp = FastMCP("financial-datasets")

_BASE = "https://api.financialdatasets.ai"


async def _get(url: str) -> dict:
    headers = {}
    if key := os.environ.get("FINANCIAL_DATASETS_API_KEY"):
        headers["X-API-KEY"] = key
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, timeout=30.0)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}


@mcp.tool()
async def get_income_statements(ticker: str, period: str = "annual", limit: int = 4) -> str:
    """Income statements for a US-listed company.

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
        period: annual | quarterly | ttm
        limit: number of periods to return (default 4)
    """
    data = await _get(f"{_BASE}/financials/income-statements/?ticker={ticker}&period={period}&limit={limit}")
    rows = data.get("income_statements", [])
    return json.dumps(rows, indent=2) if rows else "No income statements found."


@mcp.tool()
async def get_balance_sheets(ticker: str, period: str = "annual", limit: int = 4) -> str:
    """Balance sheets for a US-listed company.

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
        period: annual | quarterly | ttm
        limit: number of periods to return (default 4)
    """
    data = await _get(f"{_BASE}/financials/balance-sheets/?ticker={ticker}&period={period}&limit={limit}")
    rows = data.get("balance_sheets", [])
    return json.dumps(rows, indent=2) if rows else "No balance sheets found."


@mcp.tool()
async def get_cash_flow_statements(ticker: str, period: str = "annual", limit: int = 4) -> str:
    """Cash flow statements for a US-listed company.

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
        period: annual | quarterly | ttm
        limit: number of periods to return (default 4)
    """
    data = await _get(f"{_BASE}/financials/cash-flow-statements/?ticker={ticker}&period={period}&limit={limit}")
    rows = data.get("cash_flow_statements", [])
    return json.dumps(rows, indent=2) if rows else "No cash flow statements found."


@mcp.tool()
async def get_current_stock_price(ticker: str) -> str:
    """Current / latest price snapshot for a US-listed stock.

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
    """
    data = await _get(f"{_BASE}/prices/snapshot/?ticker={ticker}")
    snapshot = data.get("snapshot", {})
    return json.dumps(snapshot, indent=2) if snapshot else "No price data found."


@mcp.tool()
async def get_historical_stock_prices(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "day",
    interval_multiplier: int = 1,
) -> str:
    """Historical OHLCV prices for a US-listed stock.

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        interval: minute | hour | day | week | month (default day)
        interval_multiplier: multiplier on interval (default 1)
    """
    url = (
        f"{_BASE}/prices/?ticker={ticker}"
        f"&interval={interval}&interval_multiplier={interval_multiplier}"
        f"&start_date={start_date}&end_date={end_date}"
    )
    data = await _get(url)
    prices = data.get("prices", [])
    return json.dumps(prices, indent=2) if prices else "No price data found."


@mcp.tool()
async def get_company_news(ticker: str) -> str:
    """Recent news articles for a US-listed company.

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
    """
    data = await _get(f"{_BASE}/news/?ticker={ticker}")
    news = data.get("news", [])
    return json.dumps(news, indent=2) if news else "No news found."


@mcp.tool()
async def get_sec_filings(ticker: str, limit: int = 10, filing_type: str | None = None) -> str:
    """SEC filings for a US-listed company (10-K, 10-Q, 8-K, etc.).

    Args:
        ticker: Ticker symbol (e.g. AAPL, NVDA)
        limit: number of filings to return (default 10)
        filing_type: filter by type — 10-K | 10-Q | 8-K | etc. (optional)
    """
    url = f"{_BASE}/filings/?ticker={ticker}&limit={limit}"
    if filing_type:
        url += f"&filing_type={filing_type}"
    data = await _get(url)
    filings = data.get("filings", [])
    return json.dumps(filings, indent=2) if filings else "No SEC filings found."


if __name__ == "__main__":
    logger.info("Financial Datasets MCP server starting (equities + SEC only)...")
    mcp.run(transport="stdio")
