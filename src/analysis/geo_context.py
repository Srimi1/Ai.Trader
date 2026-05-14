"""
Geopolitical + macro context for trading decisions.
Python 3.9 compatible. No MCP dependency. Sync.

Used directly by decision_agent.py and orchestrator.py.
Full GDELT queries still in src/mcp/worldmonitor_finance.py (needs Python 3.10).
"""
import json
import logging
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

_PROJECT = Path(__file__).parents[2]
_CACHE_DIR = _PROJECT / "data" / "cache" / "worldmonitor"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── ticker → country ──────────────────────────────────────────────────────────
_TICKER_COUNTRY = {
    "XOM": "US", "CVX": "US", "COP": "US", "SLB": "US",
    "BP": "GB", "SHEL": "GB", "TTE": "FR",
    "LMT": "US", "RTX": "US", "NOC": "US", "BA": "US", "GD": "US",
    "ZIM": "IL", "TSM": "TW",
    "NVDA": "US", "INTC": "US", "AMD": "US", "AVGO": "US", "QCOM": "US",
    "AAPL": "US", "MSFT": "US", "GOOGL": "US", "META": "US", "AMZN": "US",
    "JPM": "US", "BAC": "US", "GS": "US", "V": "US", "MA": "US",
    "UNH": "US", "JNJ": "US", "LLY": "US", "PFE": "US",
    "WMT": "US", "COST": "US", "MCD": "US", "NKE": "US",
    "T": "US", "VZ": "US", "TMUS": "US",
}

_HIGH_RISK  = {"IR", "RU", "CN", "KP", "SY", "MM", "SD", "YE"}
_MEDIUM_RISK = {"TW", "IL", "LB", "AF", "IQ", "SA"}

_TAIWAN_EXPOSED   = {"TSM", "NVDA", "AMD", "INTC", "AVGO", "QCOM", "AMAT", "ASML"}
_HORMUZ_EXPOSED   = {"XOM", "CVX", "COP", "BP", "SHEL", "TTE", "SLB", "HAL"}
_DEFENCE_TICKERS  = {"LMT", "RTX", "NOC", "GD", "BA", "HII", "LDOS"}

# ── cache ─────────────────────────────────────────────────────────────────────

def _cache_get(key: str, ttl_hours: int = 2) -> Optional[dict]:
    p = _CACHE_DIR / f"{key}.json"
    if not p.exists():
        return None
    if (time.time() - p.stat().st_mtime) > ttl_hours * 3600:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _cache_set(key: str, data: dict) -> None:
    try:
        with open(_CACHE_DIR / f"{key}.json", "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# ── geo risk score (pure calc, no network) ────────────────────────────────────

def get_geo_risk(ticker: str) -> dict:
    """
    Return geopolitical risk score 0-10 for a ticker.
    Pure calculation — no network call, instant.
    """
    ticker = ticker.upper().strip()
    country = _TICKER_COUNTRY.get(ticker, "US")

    if country in _HIGH_RISK:
        base, country_note = 8.0, f"{country} subject to major sanctions"
    elif country in _MEDIUM_RISK:
        base, country_note = 5.0, f"{country} elevated geopolitical risk"
    else:
        base, country_note = 1.0, f"{country} standard risk"

    adj, sector_note = 0.0, ""
    if ticker in _TAIWAN_EXPOSED:
        adj += 2.5
        sector_note = "Taiwan Strait: semiconductor supply chain risk"
    if ticker in _HORMUZ_EXPOSED:
        adj += 1.5
        sector_note = "Hormuz/Red Sea: oil supply route risk"
    if ticker in _DEFENCE_TICKERS:
        adj -= 1.5
        sector_note = "Defence: benefits from geopolitical tension"

    score = min(10.0, max(0.0, round(base + adj, 1)))
    label = "HIGH" if score >= 7 else "MODERATE" if score >= 4 else "LOW"

    return {
        "ticker": ticker,
        "risk_score": score,
        "risk_label": label,
        "country_exposure": country,
        "country_note": country_note,
        "sector_note": sector_note,
        "recommendation": (
            "Reduce position size. Monitor for escalation." if score >= 7
            else "Standard due diligence." if score >= 4
            else "Minimal geo-risk adjustment needed."
        ),
    }


# ── macro snapshot (yfinance, no GDELT) ──────────────────────────────────────

def get_macro_snapshot() -> dict:
    """Fetch VIX, 10Y yield, oil, gold. Cached 1 hour."""
    cached = _cache_get("macro_snapshot_py39", ttl_hours=1)
    if cached:
        return cached

    try:
        import yfinance as yf
        symbols = {"vix": "^VIX", "yield_10y": "^TNX", "oil_wti": "CL=F", "gold": "GC=F"}
        result: dict = {"as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
        for name, sym in symbols.items():
            try:
                hist = yf.Ticker(sym).history(period="5d", interval="1d", auto_adjust=True)
                if not hist.empty and len(hist) >= 2:
                    cur = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    chg = round((cur - prev) / prev * 100, 2) if prev else 0.0
                    result[name] = {"value": round(cur, 2), "change_1d_pct": chg}
                else:
                    result[name] = {"value": None, "change_1d_pct": None}
            except Exception:
                result[name] = {"value": None, "change_1d_pct": None}

        vix = result.get("vix", {}).get("value")
        result["market_regime"] = (
            "calm" if vix and vix < 15
            else "normal" if vix and vix < 20
            else "elevated" if vix and vix < 25
            else "high fear" if vix and vix < 30
            else "extreme fear" if vix
            else "unknown"
        )
        result["vix_risk_multiplier"] = (
            1.10 if vix and vix < 15
            else 1.00 if vix and vix < 20
            else 0.90 if vix and vix < 25
            else 0.75 if vix and vix < 30
            else 0.50 if vix
            else 1.0
        )
        _cache_set("macro_snapshot_py39", result)
        return result
    except Exception as e:
        logger.warning("macro_snapshot failed: %s", e)
        return {"as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "error": str(e)}


# ── combined context for decision_agent ──────────────────────────────────────

def get_context_for_ticker(ticker: str) -> dict:
    """Single call: geo risk + macro. Used by decision_agent.py."""
    return {
        "geo_risk": get_geo_risk(ticker),
        "market": get_macro_snapshot(),
    }


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    geo = get_geo_risk(t)
    macro = get_macro_snapshot()
    print(f"{t}: geo risk {geo['risk_score']}/10 ({geo['risk_label']}) | {geo['sector_note'] or 'no sector note'}")
    print(f"VIX={macro.get('vix', {}).get('value')} | regime={macro.get('market_regime')} | multiplier={macro.get('vix_risk_multiplier')}")
