"""VectorBT backtest adapter — vectorized, fast, primary engine."""
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import vectorbt as vbt
import yfinance as yf

from src.backtesting.engine import BacktestEngine, BacktestMetrics

warnings.filterwarnings("ignore", category=RuntimeWarning)


class VectorBTAdapter(BacktestEngine):
    name = "vectorbt"

    def __init__(self):
        self._signals: list[dict] = []
        self._hold_days: int = 30
        self._max_position_pct: float = 0.05
        self._prices: Optional[pd.DataFrame] = None
        self._pf: Optional[vbt.Portfolio] = None
        self._tickers: list[str] = []

    def load_signals(
        self,
        signals: list[dict],
        hold_days: int = 30,
        max_position_pct: float = 0.05,
    ) -> None:
        self._signals = [s for s in signals if s.get("ticker")]
        self._hold_days = hold_days
        self._max_position_pct = max_position_pct
        self._tickers = sorted({s["ticker"] for s in self._signals})

    def _fetch_prices(self, start: str, end: str) -> pd.DataFrame:
        """Download adjusted close prices for all tickers + SPY benchmark."""
        tickers = list(dict.fromkeys(self._tickers + ["SPY"]))  # preserve order, dedupe
        data = yf.download(
            tickers,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        if data.empty:
            raise ValueError("No price data returned from yfinance")

        # Handle both MultiIndex (multiple tickers) and single ticker
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"]
        else:
            close = data[["Close"]].rename(columns={"Close": tickers[0]})

        close = close.dropna(how="all")
        return close

    def _build_signals(self, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Return (entries, exits, size) DataFrames aligned with prices index."""
        idx = prices.index
        tickers = [c for c in prices.columns if c != "SPY"]

        entries = pd.DataFrame(False, index=idx, columns=tickers)
        exits = pd.DataFrame(False, index=idx, columns=tickers)
        size = pd.DataFrame(0.0, index=idx, columns=tickers)

        for sig in self._signals:
            ticker = sig["ticker"]
            if ticker not in tickers:
                continue
            try:
                tx_date = pd.Timestamp(sig["transaction_date"])
            except (ValueError, KeyError):
                continue

            # Find nearest trading day on or after transaction date
            mask = idx >= tx_date
            if not mask.any():
                continue
            entry_idx = idx[mask][0]

            # Find exit date (hold_days after entry)
            entry_loc = idx.get_loc(entry_idx)
            exit_loc = min(entry_loc + self._hold_days, len(idx) - 1)
            exit_idx = idx[exit_loc]

            if sig.get("final_signal") == "BUY":
                entries.loc[entry_idx, ticker] = True
                exits.loc[exit_idx, ticker] = True
                score = abs(sig.get("adjusted_score", 1.0))
                position = min(score / 3.0, self._max_position_pct)
                size.loc[entry_idx, ticker] = position

            elif sig.get("final_signal") == "SELL":
                exits.loc[entry_idx, ticker] = True

        return entries, exits, size

    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_cash: float = 100_000.0,
    ) -> BacktestMetrics:
        if not self._signals:
            raise ValueError("No signals loaded. Call load_signals() first.")

        # Default date range from signals ± padding
        dates = pd.to_datetime([s["transaction_date"] for s in self._signals if s.get("transaction_date")])
        if start_date is None:
            start_date = (dates.min() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (dates.max() + pd.Timedelta(days=self._hold_days + 30)).strftime("%Y-%m-%d")

        prices = self._fetch_prices(start_date, end_date)
        self._prices = prices

        entries, exits, size = self._build_signals(prices)
        tickers = entries.columns.tolist()
        asset_prices = prices[tickers]

        # Drop columns with no signals to avoid empty portfolio issues
        active = entries.any() | exits.any()
        if not active.any():
            raise ValueError("No active signals mapped to price data.")

        entries = entries.loc[:, active]
        exits = exits.loc[:, active]
        size = size.loc[:, active]
        asset_prices = asset_prices.loc[:, active]

        self._pf = vbt.Portfolio.from_signals(
            close=asset_prices,
            entries=entries,
            exits=exits,
            size=size,
            init_cash=initial_cash,
            fees=0.001,
            slippage=0.001,
            freq="1d",
            direction="longonly",
        )

        return self._extract_metrics(prices)

    def _extract_metrics(self, prices: pd.DataFrame) -> BacktestMetrics:
        pf = self._pf
        if pf is None:
            raise RuntimeError("Portfolio not initialized. Call run() first.")

        # Total return
        total_ret = float(pf.total_return().mean() if hasattr(pf.total_return(), "mean") else pf.total_return())

        # Sharpe
        sharpe = float(pf.sharpe_ratio().mean() if hasattr(pf.sharpe_ratio(), "mean") else pf.sharpe_ratio())

        # Max drawdown
        mdd = float(pf.max_drawdown().mean() if hasattr(pf.max_drawdown(), "mean") else pf.max_drawdown())

        # Trades
        trades = pf.trades
        num_trades = len(trades.records) if hasattr(trades, "records") else 0
        win_rate = float(trades.win_rate().mean() if hasattr(trades, "win_rate") and num_trades else 0.0)
        profit_factor = float(trades.profit_factor().mean() if hasattr(trades, "profit_factor") and num_trades else 0.0)
        avg_ret = float(trades.return_.mean() if hasattr(trades, "return_") and num_trades else 0.0)

        # Benchmark (SPY)
        benchmark_ret = 0.0
        if "SPY" in prices.columns and len(prices) > 1:
            spy = prices["SPY"].dropna()
            benchmark_ret = float((spy.iloc[-1] / spy.iloc[0]) - 1)

        excess = total_ret - benchmark_ret

        # Calmar
        calmar = abs(total_ret / mdd) if mdd != 0 else 0.0

        # Volatility (annualized)
        value = pf.value()
        if hasattr(value, "mean"):
            value = value.mean(axis=1)
        returns = value.pct_change().dropna()
        vol = float(returns.std() * np.sqrt(252)) if len(returns) > 1 else 0.0

        # Alpha / Beta (simplified)
        alpha, beta = 0.0, 0.0
        if "SPY" in prices.columns:
            spy = prices["SPY"].dropna()
            spy_ret = spy.pct_change().dropna()
            port_ret = returns.reindex(spy_ret.index).dropna()
            spy_ret = spy_ret.reindex(port_ret.index)
            if len(port_ret) > 10:
                cov = np.cov(port_ret, spy_ret)[0, 1]
                spy_var = np.var(spy_ret)
                beta = float(cov / spy_var) if spy_var != 0 else 0.0
                alpha = float(port_ret.mean() - beta * spy_ret.mean()) * 252

        return BacktestMetrics(
            total_return_pct=round(total_ret * 100, 2),
            sharpe_ratio=round(sharpe, 3),
            max_drawdown_pct=round(mdd * 100, 2),
            win_rate_pct=round(win_rate * 100, 2),
            profit_factor=round(profit_factor, 3),
            avg_trade_return_pct=round(avg_ret * 100, 2),
            num_trades=num_trades,
            calmar_ratio=round(calmar, 3),
            volatility_annual_pct=round(vol * 100, 2),
            alpha=round(alpha, 3),
            beta=round(beta, 3),
            benchmark_return_pct=round(benchmark_ret * 100, 2),
            excess_return_pct=round(excess * 100, 2),
        )

    def get_trades(self) -> list[dict]:
        if self._pf is None:
            return []
        records = self._pf.trades.records
        if records is None or len(records) == 0:
            return []
        df = pd.DataFrame(records)
        return df.to_dict("records")

    def plot(self, filepath: str) -> None:
        if self._pf is None:
            raise RuntimeError("Portfolio not initialized. Call run() first.")
        fig = self._pf.plot()
        fig.write_image(filepath)
