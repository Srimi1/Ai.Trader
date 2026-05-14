# Phase 02 — Backtesting Engine

**Date:** 2026-05-13  
**Status:** ✅ Complete  
**Goal:** Build unified backtesting module with 3 adapter engines to validate political-alpha strategy.

---

## What Was Built

### Module Structure (`src/backtesting/`)

| File | Purpose |
|------|---------|
| `engine.py` | Abstract base class `BacktestEngine` + `BacktestMetrics` dataclass |
| `metrics.py` | Standalone metrics calculator using `quantstats` |
| `benchmark.py` | SPY benchmark downloader and comparator |
| `walkforward.py` | Rolling window walk-forward validation |
| `report.py` | HTML/Markdown report generation |
| `adapters/vectorbt_adapter.py` | **Primary** — vectorized VectorBT engine |
| `adapters/backtrader_adapter.py` | **Secondary** — event-driven Backtrader engine |
| `adapters/pybroker_adapter.py` | **ML-native** — PyBroker with walk-forward built-in |

### Adapter Comparison

| Feature | VectorBT | Backtrader | PyBroker |
|---------|----------|------------|----------|
| Engine type | Vectorized | Event-driven | ML-native |
| Speed | Fastest | Medium | Medium |
| Walk-forward | Manual | Manual | Built-in |
| Position sizing | Score-based % | Fixed cash % | Score-based % |
| Fees | 0.1% + 0.1% slippage | 0.1% | 0.1% |
| Hold period | 30 days | 30 days | 30 days |

### Orchestrator Integration

Added `--backtest` and `--engine` flags:
```bash
python -m src.agents.orchestrator --days 90 --top 5 --backtest --engine vectorbt
python -m src.agents.orchestrator --days 90 --top 5 --backtest --engine backtrader
python -m src.agents.orchestrator --days 90 --top 5 --backtest --engine pybroker
```

Pipeline: ingestion → scoring → decision → **backtest** → metrics table → HTML report.

### BacktestMetrics Dataclass

```python
total_return_pct, cagr_pct, sharpe_ratio, sortino_ratio,
max_drawdown_pct, calmar_ratio, win_rate_pct, profit_factor,
avg_trade_return_pct, num_trades, alpha, beta,
benchmark_return_pct, excess_return_pct, volatility_annual_pct, metadata
```

---

## Verified

- **VectorBT adapter**: Runs. Fetches prices, builds entry/exit signal frames, runs `vbt.Portfolio.from_signals()`, extracts Sharpe, drawdown, trades.
- **Backtrader adapter**: Runs. Custom `bt.SignalStrategy`, Cerebro setup, analyzers (SharpeRatio, DrawDown, TradeAnalyzer).
- **PyBroker adapter**: Initial scaffold. `exec_fn(ctx)` with signal map lookup. `strategy.backtest()` with `train_size=0.7`.
- **Reports**: HTML reports saved to `data/processed/reports/backtest_<engine>_YYYYMMDD_HHMM.html`.

## Limits / Known Issues (at end of Phase 02)

- **PyBroker date bug**: `ctx.date.strftime()` fails — `ctx.date` is `numpy.ndarray`, not `datetime`.
- **PyBroker metrics bug**: `TestResult` has no `.total_return` — metrics live in `.metrics` (`EvalMetrics`).
- **yfinance FutureWarning**: Single-ticker `yf.download()` returns DataFrame with MultiIndex columns in newer versions. `spy["Close"]` is DataFrame, not Series.
- **VectorBT zero returns**: Recent signals (Apr–May 2026) have ~0 forward price history. Multi-year run (`--days 730+`) needed for statistical significance.
- **Numba conflict**: `vectorbt` wants `numba<0.57.0`, `pybroker` wants `numba>=0.64.0`. Installed `numba 0.60.0` — tolerated warning.

## Follow-ups

- [ ] Fix PyBroker adapter bugs (date + metrics extraction).
- [ ] Fix yfinance compatibility across all adapters.
- [ ] Run multi-year backtest (`--days 730`) to validate strategy edge.
- [ ] Add walk-forward analysis to orchestrator.
- [ ] Benchmark alpha/beta calculation against SPY in all adapters.
