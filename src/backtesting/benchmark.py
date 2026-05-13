"""Benchmark comparison utilities (SPY buy-and-hold)."""
import yfinance as yf


def get_spy_return(start: str, end: str) -> float:
    """Return SPY total return over date range as a decimal."""
    spy = yf.download("SPY", start=start, end=end, auto_adjust=True, progress=False)
    if spy.empty or len(spy) < 2:
        return 0.0
    return float((spy["Close"].iloc[-1] / spy["Close"].iloc[0]) - 1)


def compare_to_spy(strategy_return: float, start: str, end: str) -> dict:
    """Compare strategy return to SPY buy-and-hold."""
    spy_return = get_spy_return(start, end)
    return {
        "strategy_return_pct": round(strategy_return * 100, 2),
        "spy_return_pct": round(spy_return * 100, 2),
        "excess_return_pct": round((strategy_return - spy_return) * 100, 2),
        "beat_spy": strategy_return > spy_return,
    }
