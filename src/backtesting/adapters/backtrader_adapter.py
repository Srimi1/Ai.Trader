"""Backtrader adapter — event-driven, flexible, secondary engine."""
from datetime import datetime, timedelta
from typing import Optional

import backtrader as bt
import pandas as pd
import yfinance as yf

from src.backtesting.engine import BacktestEngine, BacktestMetrics


class _SignalStrategy(bt.Strategy):
    params = (
        ("signals", []),
        ("hold_days", 30),
        ("max_position_pct", 0.05),
    )

    def __init__(self):
        self._signal_map: dict[str, list[dict]] = {}
        for s in self.p.signals:
            self._signal_map.setdefault(s["ticker"], []).append(s)
        self._entry_dates: dict[str, datetime] = {}

    def next(self):
        today = self.datas[0].datetime.date(0)
        for ticker, sigs in self._signal_map.items():
            for sig in sigs:
                try:
                    tx_date = datetime.strptime(sig["transaction_date"][:10], "%Y-%m-%d").date()
                except (ValueError, KeyError):
                    continue
                if today == tx_date:
                    data = self.getdatabyname(ticker)
                    if sig.get("final_signal") == "BUY":
                        score = abs(sig.get("adjusted_score", 1.0))
                        size_pct = min(score / 3.0, self.p.max_position_pct)
                        cash = self.broker.getcash()
                        price = data.close[0]
                        size = int((cash * size_pct) / price)
                        if size > 0:
                            self.buy(data=data, size=size)
                            self._entry_dates[ticker] = today
                    elif sig.get("final_signal") == "SELL":
                        pos = self.getposition(data)
                        if pos.size > 0:
                            self.sell(data=data, size=pos.size)
                            self._entry_dates.pop(ticker, None)

        # Time-based exit
        for ticker, entry_date in list(self._entry_dates.items()):
            if (today - entry_date).days >= self.p.hold_days:
                data = self.getdatabyname(ticker)
                pos = self.getposition(data)
                if pos.size > 0:
                    self.sell(data=data, size=pos.size)
                    self._entry_dates.pop(ticker, None)


class BacktraderAdapter(BacktestEngine):
    name = "backtrader"

    def __init__(self):
        self._signals: list[dict] = []
        self._hold_days: int = 30
        self._max_position_pct: float = 0.05
        self._cerebro: Optional[bt.Cerebro] = None

    def load_signals(
        self,
        signals: list[dict],
        hold_days: int = 30,
        max_position_pct: float = 0.05,
    ) -> None:
        self._signals = [s for s in signals if s.get("ticker")]
        self._hold_days = hold_days
        self._max_position_pct = max_position_pct

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

        # Batch download all tickers at once
        combined = yf.download(
            tickers,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False,
        )
        if combined.empty:
            raise ValueError("No price data returned from yfinance")

        cerebro = bt.Cerebro(stdstats=True)
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=0.001)

        for ticker in tickers:
            try:
                if isinstance(combined.columns, pd.MultiIndex):
                    df = combined["Close"][[ticker]].dropna().rename(columns={ticker: "close"})
                    df["open"] = combined["Open"][ticker].reindex(df.index)
                    df["high"] = combined["High"][ticker].reindex(df.index)
                    df["low"] = combined["Low"][ticker].reindex(df.index)
                    df["volume"] = combined["Volume"][ticker].reindex(df.index)
                else:
                    df = combined[["Close"]].dropna().rename(columns={"Close": "close"})
                    df["open"] = combined["Open"].reindex(df.index)
                    df["high"] = combined["High"].reindex(df.index)
                    df["low"] = combined["Low"].reindex(df.index)
                    df["volume"] = combined["Volume"].reindex(df.index)

                df = df.reset_index()
                data = bt.feeds.PandasData(
                    dataname=df,
                    datetime=0,
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                )
                cerebro.adddata(data, name=ticker)
            except Exception as _feed_err:
                import logging
                logging.getLogger(__name__).warning("Skipping ticker %s: %s", ticker, _feed_err)
                continue

        cerebro.addstrategy(
            _SignalStrategy,
            signals=self._signals,
            hold_days=self._hold_days,
            max_position_pct=self._max_position_pct,
        )

        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.0)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        results = cerebro.run()
        strat = results[0]
        self._cerebro = cerebro

        # Extract metrics
        sharpe = strat.analyzers.sharpe.get_analysis()
        dd = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        returns = strat.analyzers.returns.get_analysis()

        total_ret = returns.get("rtot", 0.0)
        sharpe_val = sharpe.get("sharperatio", 0.0)
        mdd = dd.get("max", {}).get("drawdown", 0.0)

        num_trades = 0
        win_rate = 0.0
        profit_factor = 0.0
        avg_ret = 0.0
        if trades and "total" in trades:
            num_trades = trades["total"].get("total", 0)
            won = trades["won"].get("total", 0) if "won" in trades else 0
            win_rate = won / num_trades if num_trades else 0.0
            gross_won = trades.get("won", {}).get("pnl", {}).get("total", 0)
            gross_lost = abs(trades.get("lost", {}).get("pnl", {}).get("total", 0))
            profit_factor = gross_won / gross_lost if gross_lost else 0.0
            avg_ret = trades.get("pnl", {}).get("net", {}).get("average", 0)

        # Simplified benchmark
        benchmark_ret = 0.0
        try:
            spy = yf.download("SPY", start=start_date, end=end_date, auto_adjust=True, progress=False)
            if not spy.empty:
                if isinstance(spy.columns, pd.MultiIndex):
                    spy.columns = [col[0] for col in spy.columns]
                close_vals = spy["Close"].squeeze()
                if hasattr(close_vals, "iloc") and len(close_vals) > 1 and close_vals.iloc[0] != 0:
                    benchmark_ret = float((close_vals.iloc[-1] / close_vals.iloc[0]) - 1)
        except Exception as _bench_err:
            import logging
            logging.getLogger(__name__).warning("SPY benchmark fetch failed: %s", _bench_err)

        excess = total_ret - benchmark_ret
        # mdd from backtrader DrawDown is already a % (e.g. 5.2 means 5.2%); convert to decimal
        mdd_dec = mdd / 100 if mdd else 0.0
        calmar = abs(total_ret / mdd_dec) if mdd_dec else 0.0

        return BacktestMetrics(
            total_return_pct=round(total_ret * 100, 2),
            sharpe_ratio=round(sharpe_val, 3) if sharpe_val else 0.0,
            max_drawdown_pct=round(mdd, 2),
            win_rate_pct=round(win_rate * 100, 2),
            profit_factor=round(profit_factor, 3),
            avg_trade_return_pct=round(avg_ret, 2),
            num_trades=num_trades,
            calmar_ratio=round(calmar, 3),
            benchmark_return_pct=round(benchmark_ret * 100, 2),
            excess_return_pct=round(excess * 100, 2),
        )

    def get_trades(self) -> list[dict]:
        return []

    def plot(self, filepath: str) -> None:
        if self._cerebro is None:
            raise RuntimeError("Cerebro not initialized. Call run() first.")
        self._cerebro.plot(style="candlestick", savefig=filepath)
