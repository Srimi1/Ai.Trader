"""
WorldMonitor data integration for AI.Trader.

Reads curated symbol/entity data from the cloned worldmonitor repo at
<project_root>/worldmonitor/, then fetches live macro context via yfinance
using worldmonitor's symbol lists.

Data extracted:
  - stocks.json       → US stock universe (25 major names)
  - commodities.json  → VIX, Gold, Oil, FX symbols
  - sectors.json      → 12 sector ETF symbols
  - entity-graph.json → active geopolitical hotspot nodes + edges
  - rss-allowed-domains.json → 295 curated news domains
"""
import json
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

_WM_ROOT = Path(__file__).parents[2] / "worldmonitor" / "scripts"
_SHARED = _WM_ROOT / "shared"
_DATA = _WM_ROOT / "data"

# ── static data loaders ───────────────────────────────────────────────────────

def load_stock_symbols() -> list:
    """Return worldmonitor's curated global stock list."""
    with open(_SHARED / "stocks.json") as f:
        data = json.load(f)
    return data.get("symbols", [])


def load_us_stock_symbols() -> list:
    """US-only stocks (no exchange suffix, no index tickers)."""
    return [
        s for s in load_stock_symbols()
        if "." not in s["symbol"] and not s["symbol"].startswith("^")
    ]


def load_commodity_symbols() -> list:
    """Return worldmonitor's commodity + FX symbol list."""
    with open(_SHARED / "commodities.json") as f:
        data = json.load(f)
    return data.get("commodities", [])


def load_sector_etfs() -> list:
    """Return the 12 sector ETF symbols worldmonitor tracks."""
    with open(_SHARED / "sectors.json") as f:
        data = json.load(f)
    return data.get("sectors", [])


def load_entity_graph() -> dict:
    """Return geopolitical entity graph: aliases, nodes, edges."""
    with open(_DATA / "entity-graph.json") as f:
        return json.load(f)


def load_rss_domains() -> list:
    """Return 295 curated news domains from worldmonitor."""
    with open(_SHARED / "rss-allowed-domains.json") as f:
        return json.load(f)


# ── live macro snapshot ───────────────────────────────────────────────────────

_KEY_MACRO = {
    "vix":    "^VIX",
    "spy":    "^GSPC",
    "gold":   "GC=F",
    "oil":    "CL=F",
    "dxy":    "DX-Y.NYB",
    "tnx":    "^TNX",   # 10Y Treasury yield
}

_SECTOR_ETFS = {row["name"]: row["symbol"] for row in [
    {"symbol": "XLK", "name": "Technology"},
    {"symbol": "XLF", "name": "Financials"},
    {"symbol": "XLE", "name": "Energy"},
    {"symbol": "XLV", "name": "Health Care"},
    {"symbol": "XLY", "name": "Consumer Disc."},
    {"symbol": "XLI", "name": "Industrials"},
    {"symbol": "XLP", "name": "Con. Staples"},
    {"symbol": "XLU", "name": "Utilities"},
    {"symbol": "XLB", "name": "Materials"},
    {"symbol": "XLRE", "name": "Real Estate"},
    {"symbol": "XLC", "name": "Comm. Svcs"},
    {"symbol": "SMH", "name": "Semiconductors"},
]}


def _fetch_close(symbols: list, days: int = 22) -> pd.DataFrame:
    """Fetch closing prices for a list of Yahoo Finance symbols."""
    end = datetime.now()
    start = end - timedelta(days=days + 7)  # buffer for weekends
    tickers = " ".join(symbols)
    df = yf.download(tickers, start=start.strftime("%Y-%m-%d"),
                     end=end.strftime("%Y-%m-%d"), progress=False)
    # flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df = df["Close"] if "Close" in df.columns.get_level_values(0) else df.iloc[:, 0:len(symbols)]
        if isinstance(df, pd.Series):
            df = df.to_frame()
    else:
        df = df[["Close"]] if "Close" in df.columns else df
    return df.dropna(how="all")


def get_macro_snapshot(lookback_days: int = 20) -> dict:
    """
    Fetch current macro indicators from worldmonitor's symbol universe.

    Returns a dict with spot values and % returns over lookback_days:
      {
        'vix': {'current': 18.5, 'change_pct': -2.1},
        'spy': {'current': 520.1, 'change_pct': +1.4},
        ...
        'sectors': {'Technology': {'etf': 'XLK', 'return_pct': 3.2}, ...},
        'as_of': '2026-05-13',
      }
    """
    macro_symbols = list(_KEY_MACRO.values())
    sector_symbols = list(_SECTOR_ETFS.values())
    all_symbols = macro_symbols + sector_symbols

    try:
        df = _fetch_close(all_symbols, days=lookback_days + 10)
    except Exception as e:
        return {"error": str(e), "as_of": datetime.now().strftime("%Y-%m-%d")}

    result: dict = {"sectors": {}, "as_of": datetime.now().strftime("%Y-%m-%d")}

    # macro key indicators
    for key, sym in _KEY_MACRO.items():
        col = sym if sym in df.columns else None
        if col is None:
            result[key] = {"current": None, "change_pct": None}
            continue
        series = df[col].dropna()
        if len(series) < 2:
            result[key] = {"current": None, "change_pct": None}
            continue
        current = float(series.iloc[-1])
        past = float(series.iloc[max(0, len(series) - lookback_days - 1)])
        change_pct = round((current - past) / past * 100, 2) if past else None
        result[key] = {"current": round(current, 2), "change_pct": change_pct}

    # sector ETF returns
    for sector_name, etf_sym in _SECTOR_ETFS.items():
        col = etf_sym if etf_sym in df.columns else None
        if col is None:
            result["sectors"][sector_name] = {"etf": etf_sym, "return_pct": None}
            continue
        series = df[col].dropna()
        if len(series) < 2:
            result["sectors"][sector_name] = {"etf": etf_sym, "return_pct": None}
            continue
        current = float(series.iloc[-1])
        past = float(series.iloc[max(0, len(series) - lookback_days - 1)])
        return_pct = round((current - past) / past * 100, 2) if past else None
        result["sectors"][sector_name] = {"etf": etf_sym, "return_pct": return_pct}

    return result


# ── VIX risk multiplier ───────────────────────────────────────────────────────

def get_vix_risk_multiplier(vix_value: Optional[float]) -> float:
    """
    Returns a score multiplier based on VIX level.
    High VIX = high fear = reduce signal confidence.

    VIX < 15:  1.10  (calm, slight boost)
    15–20:     1.00  (neutral)
    20–25:     0.90  (elevated)
    25–30:     0.75  (high fear)
    ≥ 30:      0.50  (extreme fear)
    """
    if vix_value is None:
        return 1.0
    if vix_value < 15:
        return 1.10
    if vix_value < 20:
        return 1.00
    if vix_value < 25:
        return 0.90
    if vix_value < 30:
        return 0.75
    return 0.50


# ── geopolitical hotspot context ──────────────────────────────────────────────

def get_active_hotspots() -> list:
    """
    Return active geopolitical conflict nodes from worldmonitor's entity graph.
    Each entry: {'id': 'RU', 'name': 'Russia', 'links': [...]}
    """
    graph = load_entity_graph()
    nodes = graph.get("nodes", {})
    # All nodes in the graph are considered 'active' hotspots (worldmonitor curates this)
    return [
        {"id": k, "name": v.get("name", k), "type": v.get("type", ""), "links": v.get("links", [])}
        for k, v in nodes.items()
    ]


# ── ticker → sector lookup ────────────────────────────────────────────────────

_STATIC_SECTOR_MAP = {
    # Tech
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Technology", "META": "Technology", "AVGO": "Technology",
    "ORCL": "Technology", "CRM": "Technology", "AMD": "Technology",
    "INTC": "Technology", "QCOM": "Technology", "TXN": "Technology",
    # Financials
    "JPM": "Financials", "BAC": "Financials", "V": "Financials",
    "MA": "Financials", "GS": "Financials", "MS": "Financials",
    "WFC": "Financials", "C": "Financials", "AXP": "Financials",
    # Healthcare
    "UNH": "Health Care", "LLY": "Health Care", "JNJ": "Health Care",
    "PFE": "Health Care", "ABBV": "Health Care", "MRK": "Health Care",
    "TMO": "Health Care", "ABT": "Health Care",
    # Consumer
    "AMZN": "Consumer Disc.", "TSLA": "Consumer Disc.", "NKE": "Consumer Disc.",
    "MCD": "Consumer Disc.", "SBUX": "Consumer Disc.", "HD": "Consumer Disc.",
    "WMT": "Con. Staples", "PG": "Con. Staples", "KO": "Con. Staples",
    "PEP": "Con. Staples", "COST": "Con. Staples",
    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    # Industrials
    "BA": "Industrials", "CAT": "Industrials", "GE": "Industrials",
    "LMT": "Industrials", "RTX": "Industrials", "NOC": "Industrials",
    # Comm Services
    "NFLX": "Comm. Svcs", "DIS": "Comm. Svcs", "T": "Comm. Svcs",
    "VZ": "Comm. Svcs", "CMCSA": "Comm. Svcs",
    # Semiconductors (subset)
    "TSM": "Semiconductors", "MU": "Semiconductors", "AMAT": "Semiconductors",
}


def get_sector_for_ticker(ticker: str) -> Optional[str]:
    return _STATIC_SECTOR_MAP.get(ticker.upper())


def get_sector_etf_for_ticker(ticker: str) -> Optional[str]:
    sector = get_sector_for_ticker(ticker)
    return _SECTOR_ETFS.get(sector) if sector else None


if __name__ == "__main__":
    print("=== WorldMonitor Data Summary ===")
    print(f"US stocks: {len(load_us_stock_symbols())}")
    print(f"Commodities: {len(load_commodity_symbols())}")
    print(f"Sector ETFs: {len(load_sector_etfs())}")
    print(f"Geo hotspots: {len(get_active_hotspots())}")
    print(f"RSS domains: {len(load_rss_domains())}")
    print()
    print("Fetching live macro snapshot...")
    snap = get_macro_snapshot(lookback_days=20)
    vix = snap.get("vix", {})
    spy = snap.get("spy", {})
    gold = snap.get("gold", {})
    oil = snap.get("oil", {})
    print(f"VIX:  {vix.get('current')} ({vix.get('change_pct'):+.1f}%)" if vix.get('current') else "VIX: N/A")
    print(f"SPY:  {spy.get('current')} ({spy.get('change_pct'):+.1f}%)" if spy.get('current') else "SPY: N/A")
    print(f"Gold: {gold.get('current')} ({gold.get('change_pct'):+.1f}%)" if gold.get('current') else "Gold: N/A")
    print(f"Oil:  {oil.get('current')} ({oil.get('change_pct'):+.1f}%)" if oil.get('current') else "Oil: N/A")
    print(f"VIX risk multiplier: {get_vix_risk_multiplier(vix.get('current'))}")
    print()
    print("Sector 20d returns:")
    for name, s in snap.get("sectors", {}).items():
        ret = s.get('return_pct')
        print(f"  {name:20s} ({s['etf']}): {ret:+.1f}%" if ret is not None else f"  {name:20s}: N/A")
