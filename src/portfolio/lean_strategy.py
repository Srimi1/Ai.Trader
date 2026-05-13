"""
LEAN algorithm that trades on congressional disclosure signals.

Deploy via:
  lean backtest "PoliticalTradesStrategy"

Requires lean CLI + Docker. Place this file in a LEAN project created with:
  lean create-project PoliticalTradesStrategy
"""
# This runs inside the LEAN engine runtime (not standard Python).
# The AlgorithmImports below are provided by LEAN's execution environment.
from AlgorithmImports import *  # noqa: F403  (LEAN runtime import)

import json
from pathlib import Path


class PoliticalTradesStrategy(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2022, 1, 1)
        self.SetEndDate(2025, 12, 31)
        self.SetCash(100_000)

        # Load pre-scored signals from our pipeline output
        signal_path = Path(self.DataFolder) / "political_signals.json"
        self._signals: dict[str, list[dict]] = {}
        if signal_path.exists():
            with open(signal_path) as f:
                raw = json.load(f)
            for s in raw:
                date_key = s["transaction_date"][:10]
                self._signals.setdefault(date_key, []).append(s)

        self._positions: set[str] = set()
        self._hold_days = 30
        self._entry_dates: dict[str, datetime] = {}

        self.SetBrokerageModel(BrokerageName.InteractiveBrokers, AccountType.Margin)
        self.SetBenchmark("SPY")
        self.UniverseSettings.Resolution = Resolution.Daily

    def OnData(self, data: Slice):
        today = self.Time.strftime("%Y-%m-%d")
        signals = self._signals.get(today, [])

        for sig in signals:
            ticker = sig.get("ticker", "")
            if not ticker or sig.get("final_signal") != "BUY":
                continue
            symbol = self.AddEquity(ticker, Resolution.Daily).Symbol
            if symbol not in self._positions:
                score = sig.get("adjusted_score", 1.0)
                weight = min(score / 3.0, 0.05)  # cap 5% per position
                self.SetHoldings(symbol, weight)
                self._positions.add(symbol)
                self._entry_dates[symbol] = self.Time
                self.Log(f"ENTER {ticker} weight={weight:.2%} score={score:.2f}")

        # Exit positions held > hold_days
        for symbol in list(self._positions):
            if symbol in self._entry_dates:
                held = (self.Time - self._entry_dates[symbol]).days
                if held >= self._hold_days:
                    self.Liquidate(symbol)
                    self._positions.discard(symbol)
                    del self._entry_dates[symbol]
                    self.Log(f"EXIT {symbol.Value} after {held}d")

    def OnEndOfAlgorithm(self):
        self.Log(f"Final portfolio value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
