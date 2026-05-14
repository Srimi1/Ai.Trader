"""Fetch OHLCV price data via yfinance (free, no key needed)."""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    # yfinance >=0.2 returns MultiIndex columns (e.g. ('Close','MSFT')); flatten to lowercase strings
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    return df


def get_price_history(ticker: str, days: int = 365) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False)
    return _flatten_columns(df)


def get_price_on_date(ticker: str, date_str: str) -> Optional[float]:
    try:
        date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        start = date - timedelta(days=5)
        end = date + timedelta(days=1)
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False)
        if df.empty:
            return None
        df = _flatten_columns(df)
        return float(df["close"].iloc[-1])
    except Exception as e:
        logger.debug("get_price_on_date(%s, %s) failed: %s", ticker, date_str, e)
        return None


def get_return_since(ticker: str, entry_date: str, days_held: int = 30) -> Optional[float]:
    try:
        entry = datetime.strptime(entry_date[:10], "%Y-%m-%d")
        exit_date = entry + timedelta(days=days_held)
        start_price = get_price_on_date(ticker, entry_date)
        exit_price = get_price_on_date(ticker, exit_date.strftime("%Y-%m-%d"))
        if start_price is not None and exit_price is not None and start_price > 0:
            return (exit_price - start_price) / start_price
        return None
    except Exception as e:
        logger.debug("get_return_since(%s, %s) failed: %s", ticker, entry_date, e)
        return None


def get_spy_return(entry_date: str, days_held: int = 30) -> Optional[float]:
    return get_return_since("SPY", entry_date, days_held)


if __name__ == "__main__":
    df = get_price_history("NVDA", days=30)
    print(f"NVDA last 30 days:\n{df.tail(5)}")
