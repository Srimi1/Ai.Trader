"""Abstract base class for backtest engines."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BacktestMetrics:
    """Standardized backtest performance metrics."""

    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return_pct: float = 0.0
    num_trades: int = 0
    alpha: float = 0.0
    beta: float = 0.0
    benchmark_return_pct: float = 0.0
    excess_return_pct: float = 0.0
    volatility_annual_pct: float = 0.0
    metadata: dict = field(default_factory=dict)


class BacktestEngine(ABC):
    """Unified interface for strategy backtesting."""

    name: str = "abstract"

    @abstractmethod
    def load_signals(
        self,
        signals: list[dict],
        hold_days: int = 30,
        max_position_pct: float = 0.05,
    ) -> None:
        """
        Ingest political-alpha signals.

        Each signal dict must contain:
            - ticker: str
            - transaction_date: str (YYYY-MM-DD)
            - final_signal: "BUY" | "SELL" | "NEUTRAL"
            - adjusted_score: float (used for position sizing)
        """
        ...

    @abstractmethod
    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_cash: float = 100_000.0,
    ) -> BacktestMetrics:
        """Run backtest and return standardized metrics."""
        ...

    @abstractmethod
    def get_trades(self) -> list[dict]:
        """Return list of executed trades."""
        ...

    @abstractmethod
    def plot(self, filepath: str) -> None:
        """Save equity curve / drawdown chart."""
        ...
