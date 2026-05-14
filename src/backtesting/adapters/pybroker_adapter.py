"""PyBroker adapter — ML-native, walk-forward built-in, secondary engine."""
from typing import Optional

import pandas as pd
import pybroker as pb
import yfinance as yf

from src.backtesting.engine import BacktestEngine, BacktestMetrics


class PyBrokerAdapter(BacktestEngine):
    name = "pybroker"

    def __init__(self):
        self._signals: list[dict] = []
        self._hold_days: int = 30
        self._max_position_pct: float = 0.05
        self._result = None

    def load_signals(
        self,
        signals: list[dict],
        hold_days: int = 30,
        max_position_pct: float = 0.05,
    ) -> None:
        self._signals = [s for s in signals if s.get("ticker")]
        self._hold_days = hold_days
        self._max_position_pct = max_position_pct

    def _make_exec_fn(self):
        signal_map: dict[tuple[str, str], dict] = {}
        for s in self._signals:
            key = (s["ticker"], s["transaction_date"])
            signal_map[key] = s

        hold_days = self._hold_days
        max_pct = self._max_position_pct

        def exec_fn(ctx):
            today = ctx.dt.strftime("%Y-%m-%d")
            sig = signal_map.get((ctx.symbol, today))
            if sig is None:
                return

            if sig.get("final_signal") == "BUY":
                score = abs(sig.get("adjusted_score", 1.0))
                size_pct = min(score / 3.0, max_pct)
                ctx.buy_shares = ctx.calc_target_shares(size_pct)
                ctx.hold_bars = hold_days
            elif sig.get("final_signal") == "SELL":
                pos = ctx.long_pos()
                if pos:
                    ctx.sell_shares = pos.shares

        return exec_fn

    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_cash: float = 100_000.0,
    ) -> BacktestMetrics:
        if not self._signals:
            raise ValueError("No signals loaded. Call load_signals() first.")

        dates = pd.to_datetime([s["transaction_date"] for s in self._signals if s.get("transaction_date")])
        if start_date is None:
            start_date = (dates.min() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (dates.max() + pd.Timedelta(days=self._hold_days + 30)).strftime("%Y-%m-%d")

        tickers = sorted({s["ticker"] for s in self._signals})

        strategy = pb.Strategy(
            pb.YFinance(),
            start_date=start_date,
            end_date=end_date,
            config=pb.StrategyConfig(initial_cash=initial_cash, max_long_positions=len(tickers)),
        )
        strategy.add_execution(self._make_exec_fn(), tickers)
        self._result = strategy.backtest()
        return self._extract_metrics(start_date, end_date)

    def _extract_metrics(self, start_date: str, end_date: str) -> BacktestMetrics:
        res = self._result
        if res is None:
            raise RuntimeError("Backtest not run. Call run() first.")

        m = res.metrics

        total_ret = float(m.total_return_pct / 100) if m.total_return_pct is not None else 0.0
        sharpe = float(m.sharpe) if m.sharpe is not None else 0.0
        mdd = float(m.max_drawdown_pct / 100) if m.max_drawdown_pct is not None else 0.0
        win_rate = float(m.win_rate) if m.win_rate is not None else 0.0
        profit_factor = float(m.profit_factor) if m.profit_factor is not None else 0.0
        num_trades = int(m.trade_count) if m.trade_count is not None else 0
        calmar = float(m.calmar) if m.calmar is not None else 0.0

        benchmark_ret = 0.0
        try:
            spy = yf.download("SPY", start=start_date, end=end_date, auto_adjust=True, progress=False)
            if not spy.empty:
                close_vals = spy["Close"].squeeze()
                if hasattr(close_vals, "iloc"):
                    benchmark_ret = float((close_vals.iloc[-1] / close_vals.iloc[0]) - 1)
                else:
                    benchmark_ret = float((close_vals[-1] / close_vals[0]) - 1)
        except Exception as _bench_err:
            import logging
            logging.getLogger(__name__).warning("SPY benchmark fetch failed: %s", _bench_err)

        excess = total_ret - benchmark_ret

        return BacktestMetrics(
            total_return_pct=round(total_ret * 100, 2),
            sharpe_ratio=round(sharpe, 3),
            max_drawdown_pct=round(mdd * 100, 2),
            win_rate_pct=round(win_rate * 100, 2),
            profit_factor=round(profit_factor, 3),
            avg_trade_return_pct=0.0,
            num_trades=num_trades,
            calmar_ratio=round(calmar, 3),
            alpha=0.0,
            beta=0.0,
            benchmark_return_pct=round(benchmark_ret * 100, 2),
            excess_return_pct=round(excess * 100, 2),
        )

    def get_trades(self) -> list[dict]:
        if self._result is None or not hasattr(self._result, "trades"):
            return []
        df = self._result.trades
        if df is None or df.empty:
            return []
        return df.to_dict("records")

    def plot(self, filepath: str) -> None:
        if self._result is None:
            raise RuntimeError("Backtest not run. Call run() first.")
        self._result.plot().write_image(filepath)
