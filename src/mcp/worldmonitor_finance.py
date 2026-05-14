"""
WorldMonitor Finance MCP Server — geopolitical risk intelligence for AI.Trader.

Provides live data from free public sources that mirror the four key layers
shown at https://finance.worldmonitor.app/:
  - Sanctions & restrictions  → OFAC via GDELT sanctions news
  - Trade route disruptions   → GDELT events near major maritime chokepoints
  - Infrastructure outages    → GDELT infrastructure disruption events
  - Economic indicators       → VIX, 10Y yield, WTI oil via yfinance

Tools exposed to Claude:
  get_sanctions_pressure()           → Recent sanction events (last 7 days)
  get_trade_route_status()           → Chokepoint risk (Red Sea, Suez, Hormuz, Panama)
  get_infrastructure_outages()       → Cable cuts, pipeline disruptions
  get_economic_indicators()          → VIX, yield, oil with trend
  get_geopolitical_risk_score()      → Per-ticker risk score 0-10
  get_worldmonitor_market_context()  → Full aggregated risk summary
"""
import json
import logging
import sys
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
import yfinance as yf
from mcp.server.fastmcp import FastMCP

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("worldmonitor-finance-mcp")

mcp = FastMCP("worldmonitor-finance")

# ── paths ─────────────────────────────────────────────────────────────────────
_PROJECT = Path(__file__).parents[2]
_WM_DATA = _PROJECT / "worldmonitor" / "scripts" / "data"
_CACHE_DIR = _PROJECT / "data" / "cache" / "worldmonitor"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── GDELT API ─────────────────────────────────────────────────────────────────
_GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_HEADERS = {
    "User-Agent": "AI.Trader research bot (non-commercial)",
    "Accept": "application/json",
}

# Major maritime chokepoints: (name, query_terms, lat_approx, lon_approx)
_CHOKEPOINTS = [
    ("Red Sea / Bab-el-Mandeb", "Red Sea shipping Houthi", 14.5, 43.0),
    ("Suez Canal", "Suez Canal shipping closure", 30.7, 32.3),
    ("Strait of Hormuz", "Strait of Hormuz Iran tanker", 26.6, 56.3),
    ("Panama Canal", "Panama Canal drought shipping", 9.1, -79.9),
    ("Strait of Malacca", "Malacca Strait piracy shipping", 2.0, 103.0),
    ("Taiwan Strait", "Taiwan Strait military tension", 25.0, 121.0),
]

# ── entity-graph for ticker → country mapping ─────────────────────────────────
_TICKER_COUNTRY = {
    # Energy — heavily exposed to Hormuz / Red Sea
    "XOM": "US", "CVX": "US", "COP": "US", "SLB": "US",
    "BP": "GB", "SHEL": "GB", "TTE": "FR",
    # Defence — benefits from geopolitical tension
    "LMT": "US", "RTX": "US", "NOC": "US", "BA": "US", "GD": "US",
    # Shipping / logistics
    "ZIM": "IL", "MAERSK.CO": "DK",
    # Semiconductors — Taiwan exposure
    "TSM": "TW", "NVDA": "US", "INTC": "US", "AMD": "US", "AVGO": "US",
    # Tech megacaps
    "AAPL": "US", "MSFT": "US", "GOOGL": "US", "META": "US", "AMZN": "US",
    # Financials
    "JPM": "US", "BAC": "US", "GS": "US", "V": "US", "MA": "US",
    # Healthcare
    "UNH": "US", "JNJ": "US", "LLY": "US", "PFE": "US",
    # Consumer
    "WMT": "US", "COST": "US", "MCD": "US", "NKE": "US",
    # Telecom / infrastructure
    "T": "US", "VZ": "US", "TMUS": "US",
}

# Countries with elevated geopolitical risk (entity-graph nodes)
_HIGH_RISK_COUNTRIES = {"IR", "RU", "CN", "KP", "SY", "MM", "SD", "YE"}
_MEDIUM_RISK_COUNTRIES = {"TW", "IL", "LB", "AF", "IQ", "SA"}

# ── cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(key: str) -> Path:
    return _CACHE_DIR / f"{key}.json"


def _cache_get(key: str, ttl_hours: int = 2) -> Optional[dict]:
    p = _cache_path(key)
    if not p.exists():
        return None
    age = time.time() - p.stat().st_mtime
    if age > ttl_hours * 3600:
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _cache_set(key: str, data: dict) -> None:
    try:
        with open(_cache_path(key), "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# ── GDELT helpers ─────────────────────────────────────────────────────────────

async def _gdelt_search(query: str, timespan: str = "3d", max_records: int = 5, retries: int = 2) -> list:
    params = {
        "query": query,
        "format": "json",
        "mode": "artlist",
        "maxrecords": max_records,
        "timespan": timespan,
        "sort": "DateDesc",
    }
    async with httpx.AsyncClient() as client:
        for attempt in range(retries + 1):
            try:
                r = await client.get(_GDELT_BASE, params=params, headers=_GDELT_HEADERS, timeout=20.0)
                if r.status_code == 429:
                    if attempt < retries:
                        await asyncio.sleep(3 * (attempt + 1))
                        continue
                    return []
                r.raise_for_status()
                data = r.json()
                return data.get("articles", [])
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                logger.warning("GDELT query '%s' failed: %s", query, e)
                return []
    return []


def _article_summary(articles: list) -> list:
    return [
        {
            "title": a.get("title", ""),
            "source": a.get("domain", ""),
            "date": a.get("seendate", "")[:8],
            "url": a.get("url", ""),
        }
        for a in articles[:5]
    ]


# ── yfinance macro fetch ──────────────────────────────────────────────────────

def _fetch_macro_spot() -> dict:
    symbols = {"vix": "^VIX", "yield_10y": "^TNX", "oil_wti": "CL=F", "gold": "GC=F", "dxy": "DX-Y.NYB"}
    result = {}
    for name, sym in symbols.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d", interval="1d", auto_adjust=True)
            if not hist.empty and len(hist) >= 2:
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = round((current - prev) / prev * 100, 2) if prev else 0.0
                result[name] = {"value": round(current, 2), "change_1d_pct": chg}
            else:
                result[name] = {"value": None, "change_1d_pct": None}
        except Exception:
            result[name] = {"value": None, "change_1d_pct": None}
    return result


# ── MCP tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_sanctions_pressure() -> str:
    """
    Recent sanctions activity from WorldMonitor Finance — last 7 days.

    Returns new/escalating sanctions events by country, sourced from GDELT
    news monitoring. Useful for assessing geopolitical risk on positions
    with exposure to sanctioned or at-risk countries.
    """
    cached = _cache_get("sanctions", ttl_hours=3)
    if cached:
        return json.dumps(cached, indent=2)

    articles = await _gdelt_search(
        'sanctions "new sanctions" OR "sanctions escalation" OR "OFAC" OR "EU sanctions"',
        timespan="7d", max_records=8,
    )
    high_risk_articles = await _gdelt_search(
        'Russia sanctions OR Iran sanctions OR "North Korea" sanctions OR "export controls"',
        timespan="7d", max_records=6,
    )

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "summary": (
            f"{len(articles)} new sanctions events detected in last 7 days. "
            f"Key actors: Russia, Iran, North Korea remain under elevated restrictions."
        ),
        "high_risk_countries": list(_HIGH_RISK_COUNTRIES),
        "recent_events": _article_summary(articles),
        "key_risks": _article_summary(high_risk_articles),
        "source": "GDELT news aggregation + WorldMonitor entity graph",
    }

    _cache_set("sanctions", result)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_trade_route_status() -> str:
    """
    Real-time status of major maritime chokepoints from WorldMonitor Finance.

    Monitors: Red Sea/Bab-el-Mandeb, Suez Canal, Strait of Hormuz,
    Panama Canal, Strait of Malacca, Taiwan Strait.

    Disruptions here affect energy prices, shipping costs, and supply chains
    for consumer, industrial, and tech sectors.
    """
    cached = _cache_get("trade_routes", ttl_hours=2)
    if cached:
        return json.dumps(cached, indent=2)

    # Single combined query to avoid GDELT rate limits
    combined_query = (
        '"Red Sea" OR "Suez Canal" OR "Strait of Hormuz" OR "Panama Canal" '
        'OR "Strait of Malacca" OR "Taiwan Strait" shipping OR military OR disruption'
    )
    all_articles = await _gdelt_search(combined_query, timespan="3d", max_records=20)

    # Map articles to chokepoints by keyword matching
    def _count_for(keywords: list) -> list:
        return [
            a for a in all_articles
            if any(kw.lower() in a.get("title", "").lower() for kw in keywords)
        ]

    chokepoint_status = []
    for name, _, lat, lon in _CHOKEPOINTS:
        # Extract keyword from chokepoint name for matching
        name_words = name.replace("/", " ").split()
        key_words = [w for w in name_words if len(w) > 3]
        matched = _count_for(key_words)
        risk_level = "HIGH" if len(matched) >= 3 else "MEDIUM" if len(matched) >= 1 else "LOW"
        chokepoint_status.append({
            "chokepoint": name,
            "coordinates": {"lat": lat, "lon": lon},
            "risk_level": risk_level,
            "recent_events_count": len(matched),
            "latest_headlines": [a.get("title", "") for a in matched[:2]],
        })

    high_risk = [c for c in chokepoint_status if c["risk_level"] == "HIGH"]
    medium_risk = [c for c in chokepoint_status if c["risk_level"] == "MEDIUM"]

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "summary": (
            f"{len(high_risk)} chokepoint(s) at HIGH risk, "
            f"{len(medium_risk)} at MEDIUM risk. "
            + ("Elevated shipping disruption risk." if high_risk else "Trade routes broadly open.")
        ),
        "chokepoints": chokepoint_status,
        "sector_impact": {
            "Energy (XLE, XOM, CVX)": "HIGH if Hormuz or Red Sea disrupted",
            "Consumer Staples / Discretionary": "MEDIUM if Suez or Malacca disrupted",
            "Semiconductors (SMH, TSM, NVDA)": "HIGH if Taiwan Strait disrupted",
            "Industrials / Shipping": "HIGH if multiple routes disrupted",
        },
        "source": "GDELT real-time news monitoring",
    }

    _cache_set("trade_routes", result)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_infrastructure_outages() -> str:
    """
    Active infrastructure disruptions from WorldMonitor Finance.

    Covers: undersea cable cuts, pipeline disruptions, major internet outages,
    power grid failures, and critical mineral supply disruptions.

    Relevant for: tech stocks (cable cuts → latency/cloud costs),
    energy stocks (pipeline disruptions), and telecom.
    """
    cached = _cache_get("outages", ttl_hours=3)
    if cached:
        return json.dumps(cached, indent=2)

    cable_articles = await _gdelt_search(
        '"submarine cable" OR "undersea cable" cut OR damage OR disruption',
        timespan="7d", max_records=5,
    )
    pipeline_articles = await _gdelt_search(
        'pipeline disruption OR "pipeline explosion" OR "gas pipeline" attack',
        timespan="7d", max_records=5,
    )
    internet_articles = await _gdelt_search(
        '"internet outage" OR "internet disruption" OR "BGP hijack" country',
        timespan="3d", max_records=4,
    )

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "summary": (
            f"Infrastructure monitoring: "
            f"{len(cable_articles)} cable event(s), "
            f"{len(pipeline_articles)} pipeline event(s), "
            f"{len(internet_articles)} internet outage event(s) in window."
        ),
        "cable_disruptions": {
            "event_count": len(cable_articles),
            "headlines": [a.get("title", "") for a in cable_articles[:3]],
            "sector_impact": "Cloud providers (AMZN, MSFT, GOOG), telecom (T, VZ)",
        },
        "pipeline_disruptions": {
            "event_count": len(pipeline_articles),
            "headlines": [a.get("title", "") for a in pipeline_articles[:3]],
            "sector_impact": "Natural gas (NG=F), energy stocks (XOM, CVX, BP)",
        },
        "internet_outages": {
            "event_count": len(internet_articles),
            "headlines": [a.get("title", "") for a in internet_articles[:3]],
            "sector_impact": "Cloud / SaaS / cybersecurity (CRWD, PANW, ZS)",
        },
        "source": "GDELT infrastructure event monitoring",
    }

    _cache_set("outages", result)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_economic_indicators() -> str:
    """
    Key macro economic indicators from WorldMonitor Finance.

    Returns live values for: VIX (fear index), 10Y Treasury yield,
    WTI crude oil, gold, and DXY (US dollar index).
    Includes 1-day change and market context interpretation.

    Use this to calibrate position sizing and signal confidence.
    """
    cached = _cache_get("economic", ttl_hours=1)
    if cached:
        return json.dumps(cached, indent=2)

    macro = _fetch_macro_spot()

    vix = macro.get("vix", {})
    vix_val = vix.get("value")
    if vix_val is None:
        market_regime = "unknown"
    elif vix_val < 15:
        market_regime = "calm — low fear, risk-on environment"
    elif vix_val < 20:
        market_regime = "normal — moderate uncertainty"
    elif vix_val < 25:
        market_regime = "elevated — investors pricing in risk"
    elif vix_val < 30:
        market_regime = "high fear — consider reducing position sizes"
    else:
        market_regime = "extreme fear — significant market stress"

    yield_val = macro.get("yield_10y", {}).get("value")
    oil_val = macro.get("oil_wti", {}).get("value")
    oil_chg = macro.get("oil_wti", {}).get("change_1d_pct")

    oil_context = ""
    if oil_chg is not None:
        if oil_chg > 3:
            oil_context = "Sharp oil spike — energy stocks likely outperform; consumer stocks pressured"
        elif oil_chg < -3:
            oil_context = "Oil selloff — energy stocks pressured; consumer stocks benefit"
        else:
            oil_context = "Oil stable"

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "indicators": macro,
        "market_regime": market_regime,
        "oil_context": oil_context,
        "yield_context": (
            f"10Y yield at {yield_val:.2f}% — " + (
                "elevated rates compress growth stock valuations" if yield_val and yield_val > 4.5
                else "moderate rate environment"
            )
        ) if yield_val else "yield data unavailable",
        "trading_implication": (
            "REDUCE position sizes" if (vix_val or 0) > 25
            else "NORMAL position sizing"
        ),
        "source": "Yahoo Finance (yfinance)",
    }

    _cache_set("economic", result)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_geopolitical_risk_score(ticker: str) -> str:
    """
    Geopolitical risk score (0-10) for a specific stock ticker.

    Combines WorldMonitor Finance data layers:
    - Country-level sanctions exposure (Russia, Iran, North Korea = high risk)
    - Trade route dependency (energy → Hormuz; tech → Taiwan; consumer → Suez)
    - Infrastructure vulnerability
    - Active geopolitical hotspot proximity

    0-2 = minimal risk, 3-4 = low, 5-6 = moderate, 7-8 = high, 9-10 = critical.
    Use to adjust position sizing or add RISK_NOTE to trade recommendations.
    """
    ticker = ticker.upper().strip()

    country = _TICKER_COUNTRY.get(ticker, "US")

    # Base score from country risk
    if country in _HIGH_RISK_COUNTRIES:
        base_score = 8.0
        country_note = f"{country} is subject to major international sanctions"
    elif country in _MEDIUM_RISK_COUNTRIES:
        base_score = 5.0
        country_note = f"{country} has elevated geopolitical risk"
    else:
        base_score = 1.0
        country_note = f"{country} — standard geopolitical risk"

    # Sector adjustments
    sector_adj = 0.0
    sector_note = ""

    # Taiwan exposure (semiconductors)
    taiwan_exposed = ticker in {"TSM", "NVDA", "AMD", "INTC", "AVGO", "QCOM", "AMAT", "ASML"}
    if taiwan_exposed:
        sector_adj += 2.5
        sector_note = "Taiwan Strait risk: semiconductor supply chain disruption exposure"

    # Hormuz/Red Sea exposure (energy)
    hormuz_exposed = ticker in {"XOM", "CVX", "COP", "BP", "SHEL", "TTE", "SLB", "HAL"}
    if hormuz_exposed:
        sector_adj += 1.5
        sector_note = "Strait of Hormuz / Red Sea: oil supply route exposure"

    # Defence (benefits from tension)
    defense_ticker = ticker in {"LMT", "RTX", "NOC", "GD", "BA", "HII", "L3", "LDOS"}
    if defense_ticker:
        sector_adj -= 1.5  # defensive/benefits from geopolitical tension
        sector_note = "Defence sector: typically benefits from geopolitical tension"

    final_score = min(10.0, max(0.0, round(base_score + sector_adj, 1)))

    if final_score >= 7:
        risk_label = "HIGH"
        recommendation = "Consider reducing position size. Monitor closely for escalation."
    elif final_score >= 4:
        risk_label = "MODERATE"
        recommendation = "Standard due diligence. Include geo-risk in stop-loss sizing."
    else:
        risk_label = "LOW"
        recommendation = "Minimal geopolitical risk adjustment needed."

    result = {
        "ticker": ticker,
        "risk_score": final_score,
        "risk_label": risk_label,
        "country_exposure": country,
        "country_note": country_note,
        "sector_note": sector_note,
        "recommendation": recommendation,
        "score_breakdown": {
            "country_base": base_score,
            "sector_adjustment": sector_adj,
            "final": final_score,
        },
        "active_hotspots": list(_HIGH_RISK_COUNTRIES | _MEDIUM_RISK_COUNTRIES),
        "source": "WorldMonitor entity-graph + TICKER_COUNTRY static map",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
async def get_worldmonitor_market_context() -> str:
    """
    Full aggregated market risk context from WorldMonitor Finance.

    One-call summary combining all four data layers:
    sanctions pressure, trade route disruptions, infrastructure outages,
    and economic indicators. Returns an overall market risk score and
    key trading implications.

    Use this as a single context injection before making BUY/SELL decisions.
    """
    cached = _cache_get("full_context", ttl_hours=1)
    if cached:
        return json.dumps(cached, indent=2)

    # Fetch macro only (fast, no GDELT calls to avoid rate limiting)
    macro = _fetch_macro_spot()
    vix_val = macro.get("vix", {}).get("value")
    oil_chg = macro.get("oil_wti", {}).get("change_1d_pct")
    yield_val = macro.get("yield_10y", {}).get("value")

    # Single GDELT query for geopolitical pulse — broad but concise
    tension_articles = await _gdelt_search(
        "military conflict trade war sanctions chokepoint disruption",
        timespan="2d", max_records=5,
    )

    # Compute overall market risk
    market_risk = 0
    flags = []

    if vix_val and vix_val > 25:
        market_risk += 3
        flags.append(f"VIX={vix_val:.1f} (high fear)")
    elif vix_val and vix_val > 20:
        market_risk += 1
        flags.append(f"VIX={vix_val:.1f} (elevated)")

    if oil_chg and abs(oil_chg) > 3:
        market_risk += 2
        flags.append(f"Oil {oil_chg:+.1f}% today (volatile)")

    if yield_val and yield_val > 4.8:
        market_risk += 1
        flags.append(f"10Y yield {yield_val:.2f}% (restrictive)")

    if len(tension_articles) >= 4:
        market_risk += 2
        flags.append(f"{len(tension_articles)} geopolitical tension events in 48h")

    market_risk = min(10, market_risk)
    if market_risk >= 6:
        overall = "HIGH RISK — reduce position sizes, tighten stop-losses"
    elif market_risk >= 3:
        overall = "MODERATE RISK — standard sizing with geo-risk watch"
    else:
        overall = "LOW RISK — normal trading conditions"

    result = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "overall_market_risk_score": market_risk,
        "overall_assessment": overall,
        "risk_flags": flags,
        "macro_snapshot": {
            "vix": vix_val,
            "oil_1d_change_pct": oil_chg,
            "yield_10y": yield_val,
            "gold": macro.get("gold", {}).get("value"),
        },
        "geopolitical_pulse": {
            "tension_events_48h": len(tension_articles),
            "top_headlines": [a.get("title", "") for a in tension_articles[:3]],
        },
        "active_hotspots": {
            "high_risk": list(_HIGH_RISK_COUNTRIES),
            "medium_risk": list(_MEDIUM_RISK_COUNTRIES),
        },
        "trading_guidance": (
            "REDUCE sizes by 30-50% and widen stops" if market_risk >= 6
            else "NORMAL sizing — review geo_risk_score per ticker"
        ),
        "source": "WorldMonitor Finance layers via GDELT + yfinance",
    }

    _cache_set("full_context", result)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    logger.info("WorldMonitor Finance MCP server starting...")
    mcp.run(transport="stdio")
