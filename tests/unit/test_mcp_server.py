"""Unit tests for the Financial Datasets MCP server — no API calls.

MCP server requires Python 3.10+ (mcp package constraint).
These tests run in the dedicated .venv-mcp environment.
In Python 3.9 venv they are auto-skipped.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

mcp_available = pytest.importorskip("mcp", reason="mcp package requires Python 3.10+ — skipped in 3.9 venv")


class TestMCPToolRegistration:
    def test_seven_tools_registered(self):
        from src.mcp.financial_datasets import mcp
        tools = mcp._tool_manager.list_tools()
        assert len(tools) == 7

    def test_no_crypto_tools(self):
        from src.mcp.financial_datasets import mcp
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        crypto_tools = {n for n in tool_names if "crypto" in n.lower()}
        assert len(crypto_tools) == 0

    def test_expected_tools_present(self):
        from src.mcp.financial_datasets import mcp
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        expected = {
            "get_income_statements",
            "get_balance_sheets",
            "get_cash_flow_statements",
            "get_current_stock_price",
            "get_historical_stock_prices",
            "get_company_news",
            "get_sec_filings",
        }
        assert expected == tool_names


class TestMCPToolLogic:
    @pytest.mark.asyncio
    async def test_income_statements_returns_json(self):
        from src.mcp.financial_datasets import get_income_statements
        mock_data = {"income_statements": [{"ticker": "AAPL", "revenue": 100000}]}
        with patch("src.mcp.financial_datasets._get", new=AsyncMock(return_value=mock_data)):
            result = await get_income_statements("AAPL")
        assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_empty_response_returns_message(self):
        from src.mcp.financial_datasets import get_income_statements
        with patch("src.mcp.financial_datasets._get", new=AsyncMock(return_value={"income_statements": []})):
            result = await get_income_statements("FAKE")
        assert "No income statements found" in result

    @pytest.mark.asyncio
    async def test_current_price_returns_json(self):
        from src.mcp.financial_datasets import get_current_stock_price
        mock_data = {"snapshot": {"ticker": "NVDA", "price": 900.0}}
        with patch("src.mcp.financial_datasets._get", new=AsyncMock(return_value=mock_data)):
            result = await get_current_stock_price("NVDA")
        assert "NVDA" in result

    @pytest.mark.asyncio
    async def test_sec_filings_with_type_filter(self):
        from src.mcp.financial_datasets import get_sec_filings
        mock_data = {"filings": [{"type": "10-K", "ticker": "AAPL"}]}
        with patch("src.mcp.financial_datasets._get", new=AsyncMock(return_value=mock_data)) as mock_get:
            result = await get_sec_filings("AAPL", filing_type="10-K")
        url_called = mock_get.call_args[0][0]
        assert "filing_type=10-K" in url_called

    @pytest.mark.asyncio
    async def test_sec_filings_no_type_no_filter_param(self):
        from src.mcp.financial_datasets import get_sec_filings
        mock_data = {"filings": [{"ticker": "AAPL"}]}
        with patch("src.mcp.financial_datasets._get", new=AsyncMock(return_value=mock_data)) as mock_get:
            result = await get_sec_filings("AAPL")
        url_called = mock_get.call_args[0][0]
        assert "filing_type" not in url_called
