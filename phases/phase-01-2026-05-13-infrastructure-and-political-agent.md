# Phase 01 — Infrastructure & Political Trades AI Agent

**Date:** 2026-05-13  
**Status:** ✅ Complete  
**Goal:** Build end-to-end data ingestion pipeline and AI agent layer for political-alpha trading signals.

---

## What Was Built

### 1. Data Ingestion Layer (`src/ingestion/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `congress.py` | Fetches congressional STOCK Act disclosures via Quiver Quantitative API | ✅ |
| `news.py` | News sentiment scraping for signal enrichment | ✅ |
| `prices.py` | Price data fetching (yfinance) | ✅ |
| `worldmonitor.py` | Integration with cloned WorldMonitor repo for macro/symbol universe | ✅ |

**Congress Ingestion Fix:**
- Replaced dead House Stock Watcher S3 URL (403 Forbidden) with Quiver Quantitative API.
- Added **3-layer resilience**: live API → stale cache (`data/cache/quiver_transactions.json`, 6h TTL) → deterministic demo seed data.
- Fetches both House and Senate transaction data.
- URL: `https://api.quiverquant.com/beta/live/congresstrading`

**API Key Testing:**
- Anthropic ✅ (Claude API for decision agent)
- Alpha Vantage ✅ (price data backup)
- Quiver Quant ⚠️ (demo key `demo` is flaky/500, but fallback chain saves it)

### 2. Analysis Layer (`src/analysis/`)

| Module | Purpose |
|--------|---------|
| `signals.py` | Signal scoring: politician influence weight + cluster bonus + news sentiment |
| `sentiment.py` | News sentiment analysis |
| `macro.py` | Macro context (VIX, sector ETF performance) |

### 3. AI Agent Layer (`src/agents/`)

| Module | Purpose |
|--------|---------|
| `decision_agent.py` | LLM-powered signal evaluation — generates BUY/HOLD/SELL with size, SL, TP |
| `risk_agent.py` | Position sizing, portfolio heat, max-drawdown guardrails |
| `orchestrator.py` | Main pipeline runner: ingestion → scoring → risk check → decision → output |

**Orchestrator CLI:**
```bash
python -m src.agents.orchestrator --days 90 --top 5 --dry-run
```

### 4. Portfolio Layer (`src/portfolio/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `backtest.py` | Portfolio backtest wrapper | ✅ |
| `lean_strategy.py` | LEAN engine strategy stub | 📝 Stub |

### 5. MCP Server (`src/mcp/`)

| Module | Purpose |
|--------|---------|
| `financial_datasets.py` | FastMCP server for Financial Datasets API (US equities + SEC filings) |

### 6. WorldMonitor Integration (v1)

- Cloned `worldmonitor/` repo at project root (TypeScript app with geopolitical data).
- `src/ingestion/worldmonitor.py` reads WorldMonitor's static data:
  - `stocks.json` — 25+ major stock symbols
  - `commodities.json` — VIX, Gold, Oil, FX symbols
  - `sectors.json` — 12 sector ETF symbols
  - `entity-graph.json` — geopolitical hotspot nodes + edges
  - `rss-allowed-domains.json` — 295 curated news domains
- Live macro snapshot via yfinance: VIX, SPY, Gold, Oil, DXY, 10Y Treasury.
- VIX risk multiplier: scales signal confidence by fear level (0.50× at VIX≥30, 1.10× at VIX<15).
- Static sector mapping for 60+ tickers → sector → ETF lookup.

---

## Verified

- Orchestrator runs full pipeline end-to-end: fetches congress data, scores signals, runs decision agent, outputs approved trades table.
- WorldMonitor data loaders return expected counts (US stocks, commodities, sectors, hotspots, RSS domains).
- Macro snapshot fetches live VIX/SPY/Gold/Oil with 20d change %.

## Limits / Known Issues

- **Signal scarcity**: Only ~60 approved BUY signals in last 90 days. Recent dates (Apr–May 2026) mean minimal forward price history for backtests.
- **Quiver demo key**: Flaky; production needs paid key.
- **WorldMonitor repo**: Not tracked by git (external clone). Needs `git clone` on fresh machines.
- **Python 3.9 compatibility**: All code uses `from typing import Optional, List, Dict` — no `str \| None` union syntax.

## Follow-ups

- [ ] Wire WorldMonitor macro context into signal scoring (VIX multiplier currently loaded but not applied in pipeline).
- [ ] Add sector-rotation overlay using WorldMonitor sector ETF returns.
- [ ] Connect geopolitical hotspot alerts to risk agent (elevated conflict = reduce position size).
