"""Backtesting engine package."""
from src.backtesting.engine import BacktestEngine, BacktestMetrics
from src.backtesting.adapters.vectorbt_adapter import VectorBTAdapter
from src.backtesting.adapters.backtrader_adapter import BacktraderAdapter
from src.backtesting.adapters.pybroker_adapter import PyBrokerAdapter
from src.backtesting.report import generate_report
from src.backtesting.walkforward import rolling_walkforward, summarize_walkforward

__all__ = [
    "BacktestEngine",
    "BacktestMetrics",
    "VectorBTAdapter",
    "BacktraderAdapter",
    "PyBrokerAdapter",
    "generate_report",
    "rolling_walkforward",
    "summarize_walkforward",
]
