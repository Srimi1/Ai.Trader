"""
Alpaca Paper Trading client for AI.Trader.

PAPER TRADING ONLY — uses paper-api.alpaca.markets endpoint.
No real money at risk.

Requires in .env:
  ALPACA_API_KEY=your_paper_key
  ALPACA_SECRET_KEY=your_paper_secret
  ALPACA_BASE_URL=https://paper-api.alpaca.markets  (default)

Sign up free at https://alpaca.markets → Paper Trading.
"""
import logging
import os
from math import floor
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("ALPACA_API_KEY", "")
_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

_PAPER_ONLY = True  # hard-coded guard — never accidentally go live


def _client():
    from alpaca.trading.client import TradingClient
    if not _API_KEY or not _SECRET_KEY:
        raise EnvironmentError(
            "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env.\n"
            "Sign up free at https://alpaca.markets → Paper Trading."
        )
    return TradingClient(
        api_key=_API_KEY,
        secret_key=_SECRET_KEY,
        paper=_PAPER_ONLY,
    )


# ── account ────────────────────────────────────────────────────────────────────

def get_account() -> dict:
    """Return account summary: cash, portfolio_value, buying_power."""
    acct = _client().get_account()
    return {
        "cash": float(acct.cash),
        "portfolio_value": float(acct.portfolio_value),
        "buying_power": float(acct.buying_power),
        "equity": float(acct.equity),
        "daytrade_count": int(acct.daytrade_count),
        "status": acct.status.value,
    }


def is_market_open() -> bool:
    """True if US equity market is currently open."""
    try:
        clock = _client().get_clock()
        return clock.is_open
    except Exception as e:
        logger.warning("Could not check market clock: %s", e)
        return False


# ── positions ──────────────────────────────────────────────────────────────────

def get_positions() -> dict:
    """Return dict of {ticker: {qty, avg_entry, current_price, unrealized_pnl_pct}}."""
    positions = _client().get_all_positions()
    result = {}
    for pos in positions:
        sym = pos.symbol
        qty = float(pos.qty)
        avg_entry = float(pos.avg_entry_price)
        current = float(pos.current_price)
        pnl_pct = ((current - avg_entry) / avg_entry * 100) if avg_entry else 0.0
        result[sym] = {
            "qty": qty,
            "avg_entry_price": avg_entry,
            "current_price": current,
            "market_value": float(pos.market_value),
            "unrealized_pnl": float(pos.unrealized_pl),
            "unrealized_pnl_pct": round(pnl_pct, 2),
            "side": pos.side.value,
        }
    return result


def get_position(ticker: str) -> Optional[dict]:
    """Return position for a single ticker, or None if not held."""
    positions = get_positions()
    return positions.get(ticker.upper())


# ── orders ─────────────────────────────────────────────────────────────────────

def place_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
) -> dict:
    """
    Place a paper trading order.

    Args:
        ticker: e.g. "NVDA"
        side: "buy" or "sell"
        qty: number of shares (fractional supported if broker allows)
        order_type: "market" (default) or "limit"

    Returns order confirmation dict.
    """
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    if qty <= 0:
        raise ValueError(f"qty must be > 0, got {qty}")

    side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    request = MarketOrderRequest(
        symbol=ticker.upper(),
        qty=qty,
        side=side_enum,
        time_in_force=TimeInForce.DAY,
    )

    try:
        order = _client().submit_order(request)
        logger.info(
            "Order placed: %s %s x%.2f @ market [id=%s]",
            side.upper(), ticker, qty, order.id,
        )
        return {
            "order_id": str(order.id),
            "ticker": ticker.upper(),
            "side": side.lower(),
            "qty": float(qty),
            "status": order.status.value,
            "filled_at": str(order.filled_at) if order.filled_at else None,
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
        }
    except Exception as e:
        logger.error("Order failed %s %s: %s", side, ticker, e)
        raise


def cancel_all_orders() -> int:
    """Cancel all open orders. Returns count cancelled."""
    cancelled = _client().cancel_orders()
    return len(cancelled) if cancelled else 0


def close_position(ticker: str) -> dict:
    """Close the entire position in a ticker at market."""
    try:
        result = _client().close_position(ticker.upper())
        return {"ticker": ticker, "status": "closed", "order_id": str(result.id)}
    except Exception as e:
        logger.error("Failed to close %s: %s", ticker, e)
        raise


# ── sizing ─────────────────────────────────────────────────────────────────────

def compute_qty(position_size_pct: float, current_price: float) -> int:
    """
    Compute integer share count for a given position size as % of portfolio.

    Args:
        position_size_pct: e.g. 0.03 = 3% of portfolio
        current_price: current stock price

    Returns: number of whole shares (min 1).
    """
    acct = get_account()
    portfolio_value = acct["portfolio_value"]
    dollar_amount = portfolio_value * position_size_pct
    shares = floor(dollar_amount / current_price)
    return max(1, shares)


def get_current_price(ticker: str) -> Optional[float]:
    """Fetch latest price via Alpaca market data (works without data subscription for basic quotes)."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        hist = t.history(period="1d", interval="1m", auto_adjust=True)
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None
    except Exception:
        return None


if __name__ == "__main__":
    import json
    print("=== Alpaca Paper Trading Account ===")
    try:
        acct = get_account()
        print(json.dumps(acct, indent=2))
        print(f"\nMarket open: {is_market_open()}")
        positions = get_positions()
        if positions:
            print(f"\nOpen positions ({len(positions)}):")
            for sym, pos in positions.items():
                print(f"  {sym}: {pos['qty']:.0f} shares @ ${pos['avg_entry_price']:.2f}"
                      f" | P&L: {pos['unrealized_pnl_pct']:+.1f}%")
        else:
            print("\nNo open positions.")
    except EnvironmentError as e:
        print(f"\nSetup needed: {e}")
