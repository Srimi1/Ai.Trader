"""Benchmark comparison utilities (SPY buy-and-hold)."""
import yfinance as yf


def get_spy_return(start: str, end: str) -> float:
    """Return SPY total return over date range as a decimal."""
    try:
        spy = yf.download("SPY", start=start, end=end, auto_adjust=True, progress=False)
    except Exception:
        return 0.0
    if spy.empty or len(spy) < 2:
        return 0.0
    # Flatten MultiIndex columns from newer yfinance versions
    if isinstance(spy.columns, __import__("pandas").MultiIndex):
        spy.columns = [col[0] for col in spy.columns]
    close_col = "Close" if "Close" in spy.columns else spy.columns[0]
    close = spy[close_col].dropna()
    if len(close) < 2 or close.iloc[0] == 0:
        return 0.0
    return float((close.iloc[-1] / close.iloc[0]) - 1)


def compare_to_spy(strategy_return: float, start: str, end: str) -> dict:
    """Compare strategy return to SPY buy-and-hold."""
    spy_return = get_spy_return(start, end)
    return {
        "strategy_return_pct": round(strategy_return * 100, 2),
        "spy_return_pct": round(spy_return * 100, 2),
        "excess_return_pct": round((strategy_return - spy_return) * 100, 2),
        "beat_spy": strategy_return > spy_return,
    }
