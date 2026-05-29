"""
AI.Trader Local API Server
Run: python scripts/start_api.py
Serves: localhost:8888

Endpoints:
  GET  /health
  GET  /scan/ultra?days=7
  GET  /scan/short?days=30&window=15
  GET  /scan/medium?days=60
  GET  /scan/long?days=365
  GET  /portfolio
  POST /portfolio  (body: {"holdings": [...]})
  GET  /signal/{ticker}
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="AI.Trader Local API",
    description="Congressional trade signal scanner for the AI.Trader Chrome extension",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extension + localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Lazy imports — keep server startup fast; scanners load on first request
# ---------------------------------------------------------------------------

def _momentum_scanner():
    from src.analysis.momentum_scanner import scan as _scan
    return _scan


def _geo_scanner():
    from src.analysis.geo_scanner import scan as _scan
    return _scan


def _committee_scanner():
    from src.analysis.committee_scanner import scan as _scan
    return _scan


def _conviction_tracker():
    from src.analysis.conviction_tracker import scan as _scan
    return _scan


def _portfolio_loader():
    from src.portfolio.tickertape import load_portfolio
    return load_portfolio


def _signals_module():
    from src.analysis.signals import score_all
    from src.ingestion.congress import get_recent_trades
    return score_all, get_recent_trades


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Holding(BaseModel):
    ticker: str
    name: Optional[str] = None
    qty: Optional[float] = None
    avg_price: Optional[float] = None
    current_price: Optional[float] = None
    invested: Optional[float] = None
    current_value: Optional[float] = None
    weight_pct: Optional[float] = None
    pnl_pct: Optional[float] = None


class PortfolioBody(BaseModel):
    holdings: List[Holding]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "server": "AI.Trader Local API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/scan/ultra")
def scan_ultra(days: int = 7):
    """Ultra-short 1-5 day bounce plays: RSI < 35 + recent congressional BUY."""
    try:
        scanner = _momentum_scanner()
        data = scanner(days=days)
        return {"ok": True, "strategy": "ultra", "days": days, "count": len(data), "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}


@app.get("/scan/short")
async def scan_short(days: int = 30, window: int = 15):
    """Short-term geo-conviction plays (10-15 day hold)."""
    try:
        scanner = _geo_scanner()
        data = await scanner(days=days, window_days=window)
        return {"ok": True, "strategy": "short", "days": days, "window": window, "count": len(data), "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}


@app.get("/scan/medium")
def scan_medium(days: int = 60):
    """Medium-term committee insider plays (15-45 day hold)."""
    try:
        scanner = _committee_scanner()
        data = scanner(days=days)
        return {"ok": True, "strategy": "medium", "days": days, "count": len(data), "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}


@app.get("/scan/long")
def scan_long(days: int = 365):
    """Long-term conviction plays (45d+ hold) from top-ranked politicians."""
    try:
        tracker = _conviction_tracker()
        data = tracker(days=days)
        return {"ok": True, "strategy": "long", "days": days, "count": len(data), "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": []}


@app.get("/portfolio")
def get_portfolio():
    """Load portfolio from local cache (tickertape.in)."""
    try:
        loader = _portfolio_loader()
        holdings = loader()
        return {"ok": True, "count": len(holdings), "holdings": holdings}
    except Exception as e:
        return {"ok": False, "error": str(e), "holdings": []}


@app.post("/portfolio")
def save_portfolio(body: PortfolioBody):
    """Persist portfolio holdings to local cache."""
    try:
        from src.portfolio.tickertape import save_portfolio as _save
        holdings = [h.model_dump() for h in body.holdings]
        _save(holdings)
        return {"ok": True, "saved": len(holdings)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/signal/{ticker}")
def signal_for_ticker(ticker: str):
    """
    Return all scored congressional trades for a single ticker.
    Includes geo risk and macro snapshot.
    """
    ticker = ticker.upper().strip()
    try:
        score_all, get_recent_trades = _signals_module()
        from src.analysis.geo_context import get_geo_risk, get_macro_snapshot

        trades = get_recent_trades(days=180)
        scored = score_all(trades)
        ticker_trades = [s for s in scored if s.get("ticker") == ticker]

        geo = get_geo_risk(ticker)
        macro = get_macro_snapshot()

        return {
            "ok": True,
            "ticker": ticker,
            "trade_count": len(ticker_trades),
            "trades": ticker_trades,
            "geo_risk": geo,
            "macro": macro,
        }
    except Exception as e:
        return {"ok": False, "ticker": ticker, "error": str(e), "trades": []}


@app.get("/performance")
def performance(horizon: int = 30):
    """
    Closed-loop performance: overall journal P&L summary plus per-source
    attribution (win rate + excess-vs-SPY) over the given outcome horizon.
    """
    try:
        from src.portfolio.journal import Journal
        from src.portfolio.scorecard import Scorecard
        return {
            "ok": True,
            "horizon_days": horizon,
            "summary": Journal().summary(),
            "attribution": Scorecard().attribution(horizon_days=horizon),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
