# Audit Report — AI.Trader — 2026-05-14

## Executive Summary

- **Files scanned:** 45 (source + tests)
- **Critical issues (P1):** 12
- **Warnings (P2):** 27
- **Improvements (P3):** 38
- **Total findings:** 77
- **Features with tests:** 6 / 16
- **Test coverage:** Partial — 10 test files, mostly unit tests, no backtesting adapter tests

---

## Critical Issues (P1)

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/analysis/sentiment.py` | 48 | Direct dict key access `trade["ticker"]` raises KeyError if key missing | Use `trade.get('ticker')` and skip or raise meaningful error |
| `src/analysis/signals.py` | 72 | Direct dict key access `trade["representative"]` raises KeyError | Use `trade.get('representative')` or validate required keys |
| `src/analysis/signals.py` | 73 | Direct dict key access `trade["amount_range"]` raises KeyError | Use `trade.get('amount_range')` or validate required keys |
| `src/analysis/signals.py` | 74 | Direct dict key access `trade["transaction_date"]` raises KeyError | Use `trade.get('transaction_date')` or validate required keys |
| `src/analysis/signals.py` | 75 | Direct dict key access `trade["ticker"]` / `trade["trade_type"]` raises KeyError | Use `.get()` accessors or validate required keys |
| `src/analysis/signals.py` | 97 | Direct dict key access `t["ticker"]` in list comprehension raises KeyError | Use `t.get('ticker')` for filter condition |
| `src/backtesting/adapters/backtrader_adapter.py` | 88 | Empty signals → `pd.to_datetime` empty → `dates.min()` ValueError | Check dates non-empty before `.min()` / `.max()` |
| `src/backtesting/adapters/pybroker_adapter.py` | 34 | Direct dict key access `s["transaction_date"]` raises KeyError | Use `s.get('transaction_date')` and skip missing |
| `src/backtesting/adapters/pybroker_adapter.py` | 67 | Empty signals → `pd.to_datetime` empty → `dates.min()` ValueError | Check dates non-empty before `.min()` / `.max()` |
| `src/backtesting/adapters/vectorbt_adapter.py` | 114 | Empty signals → `pd.to_datetime` empty → `dates.min()` ValueError | Check dates non-empty before `.min()` / `.max()` |
| `src/ingestion/worldmonitor.py` | 36 | `json.load(f).get(key, [])` raises AttributeError if JSON root is a list | Add `except AttributeError: return []` or validate dict before `.get()` |
| `src/portfolio/lean_strategy.py` | 61 | `s['transaction_date'][:10]` risks KeyError or IndexError on malformed signals | Use `s.get('transaction_date', '')[:10]` |

---

## Warnings (P2)

| File | Line | Issue | Recommendation |
|------|------|-------|----------------|
| `src/agents/orchestrator.py` | 147 | Bare `except Exception` swallows all backtest failures silently | Catch specific exceptions, log full traceback, re-raise unexpected |
| `src/agents/risk_agent.py` | 17 | `_disclosure_lag` returns 0 on ValueError, letting bad dates pass filter | Return `float('inf')` sentinel or reject unparseable dates |
| `src/analysis/macro.py` | 27 | `_sector_momentum_multiplier` hardcodes thresholds that duplicate `_SECTOR_MOMENTUM_THRESHOLDS` dict | Iterate over the dict instead of redefining inline |
| `src/analysis/macro.py` | 58 | Falsy check `if vix_val` treats VIX 0.0 as N/A | Use `vix_val is not None` |
| `src/analysis/sentiment.py` | 31 | Bare `except Exception` swallows API/network/key errors silently | Catch specific exceptions, log error, then return fallback |
| `src/backtesting/adapters/backtrader_adapter.py` | 97 | `yf.download()` no timeout — can hang indefinitely | Pass explicit `timeout` param or use timeout context |
| `src/backtesting/adapters/backtrader_adapter.py` | 137 | Bare `except Exception` swallows feed construction errors silently | Catch specific exceptions, log full traceback |
| `src/backtesting/adapters/backtrader_adapter.py` | 154 | `cerebro.run()` not wrapped in try/except — crashes entire backtest | Wrap in try/except, raise meaningful BacktestError |
| `src/backtesting/adapters/backtrader_adapter.py` | 183 | Bare `except Exception` swallows SPY benchmark fetch failures | Catch specific network/data exceptions, log traceback |
| `src/backtesting/adapters/backtrader_adapter.py` | 202 | Falsy check `if sharpe_val` treats Sharpe 0.0 as missing | Use `sharpe_val is not None` or round unconditionally |
| `src/backtesting/adapters/pybroker_adapter.py` | 82 | `strategy.backtest()` not wrapped in try/except | Wrap in try/except, raise BacktestError |
| `src/backtesting/adapters/pybroker_adapter.py` | 101 | Bare `except Exception` swallows SPY benchmark fetch failures | Catch specific exceptions, log traceback |
| `src/backtesting/adapters/pybroker_adapter.py` | 106 | Division by zero risk if SPY close starts at 0 | Guard `close_vals.iloc[0] == 0` before dividing |
| `src/backtesting/adapters/vectorbt_adapter.py` | 13 | Global `warnings.filterwarnings("ignore")` masks real arithmetic issues | Scope with `warnings.catch_warnings()` around specific call |
| `src/backtesting/adapters/vectorbt_adapter.py` | 41 | `yf.download()` no timeout — can hang indefinitely | Pass explicit `timeout` param |
| `src/backtesting/adapters/vectorbt_adapter.py` | 137 | `vbt.Portfolio.from_signals()` not wrapped in try/except | Wrap in try/except, raise BacktestError |
| `src/backtesting/adapters/vectorbt_adapter.py` | 176 | Division by zero risk if SPY close starts at 0 | Guard `spy.iloc[0] == 0` before dividing |
| `src/backtesting/benchmark.py` | 9 | Broad `except Exception` swallows yfinance/network errors silently | Catch specific exceptions, log failure before fallback |
| `src/backtesting/walkforward.py` | 70 | Broad `except Exception` prints and continues, swallowing engine failures | Log at error level, collect failures into result field |
| `src/ingestion/prices.py` | 24 | `get_price_history` calls yfinance without try/except | Wrap in try/except, return empty DataFrame or raise domain exception |
| `src/ingestion/worldmonitor.py` | 24 | `warnings.filterwarnings('ignore')` globally suppresses ALL warnings | Scope to specific module/category or use context manager |
| `src/mcp/financial_datasets.py` | 24 | `FINANCIAL_DATASETS_API_KEY` accessed without required fallback | Fail fast with clear exception, or document unauthenticated mode |
| `src/mcp/financial_datasets.py` | 29 | New `httpx.AsyncClient` per API call — TCP overhead | Create module-level client and reuse |
| `src/mcp/financial_datasets.py` | 36 | Broad `except Exception` masks bugs into generic error dict | Catch `httpx` exceptions first, log full traceback for unknown |
| `src/portfolio/lean_strategy.py` | 59 | `json.load(f)` on user file has no try/except | Wrap in try/except for `JSONDecodeError`, `OSError` |
| `src/portfolio/lean_strategy.py` | 83 | `weight = min(score / 3.0, 0.05)` can produce negative weight on BUY | Clamp: `max(0.0, min(score / 3.0, 0.05))` |
| `tests/unit/test_risk_agent.py` | 15 | `datetime.now()` called twice — midnight crossing breaks 3-day lag assertion | Capture once in local variable, derive both dates from it |

---

## Feature Completeness Matrix

| Feature | Entry Point | Tests | Connected? | Issues |
|---------|-------------|-------|------------|--------|
| Congress Ingestion | `src/ingestion/congress.py` | ✅ Unit + Integration | ✅ | — |
| News Ingestion | `src/ingestion/news.py` | ✅ Unit | ✅ | — |
| Price Ingestion | `src/ingestion/prices.py` | ✅ Integration | ✅ | — |
| WorldMonitor | `src/ingestion/worldmonitor.py` | ❌ | ⚠️ Loaded, not wired into pipeline | P1=1, P2=1, P3=4 |
| Signal Scoring | `src/analysis/signals.py` | ✅ Unit | ✅ | **P1=5**, P3=5 |
| Sentiment Analysis | `src/analysis/sentiment.py` | ✅ Unit | ✅ | P1=1, P2=1, P3=1 |
| Macro Analysis | `src/analysis/macro.py` | ❌ | ⚠️ Loaded, not wired into pipeline | P2=2, P3=1 |
| Decision Agent | `src/agents/decision_agent.py` | ✅ Unit | ✅ | — |
| Risk Agent | `src/agents/risk_agent.py` | ✅ Unit | ✅ | P2=1, P3=1 |
| Orchestrator | `src/agents/orchestrator.py` | ❌ | ✅ | P2=1, P3=2 |
| VectorBT Adapter | `src/backtesting/adapters/vectorbt_adapter.py` | ❌ | ✅ | P1=1, P2=4, P3=1 |
| Backtrader Adapter | `src/backtesting/adapters/backtrader_adapter.py` | ❌ | ✅ | P1=1, P2=5, P3=2 |
| PyBroker Adapter | `src/backtesting/adapters/pybroker_adapter.py` | ❌ | ✅ | P1=2, P2=3, P3=2 |
| Backtest Engine | `src/backtesting/engine.py` | ❌ | ✅ | — |
| MCP Server | `src/mcp/financial_datasets.py` | ✅ Unit | ✅ | P2=3 |
| LEAN Strategy | `src/portfolio/lean_strategy.py` | ❌ | 📝 Stub | P1=1, P2=2, P3=5 |

**Coverage gap:** 10 / 45 files have tests. Backtesting adapters (VectorBT, Backtrader, PyBroker) have **zero tests**.

---

## Architecture Health

### Error Handling Patterns
- **Anti-pattern dominant:** Broad `except Exception:` or `except Exception as e:` followed by `pass` / `print` / silent fallback appears in **14 files**.
- **Risk:** Bugs, network failures, and data corruption are swallowed silently. Debugging is impossible without logs.

### Dict Access Patterns
- **Anti-pattern dominant:** Direct bracket access `dict["key"]` instead of `.get()` appears in **6 locations** across `signals.py`, `sentiment.py`, `pybroker_adapter.py`, `lean_strategy.py`.
- **Risk:** `KeyError` crashes on malformed upstream data.

### Magic Numbers
- **38 P3 findings** for inline constants: `252` (trading days), `3.0` (score denominator), `0.05` (max position), `0.5` (threshold), `20/30` (VIX levels), `30` (hold days), `100_000.0` (cash), etc.
- **Recommendation:** Centralize in `src/utils/constants.py` or dataclass configs.

### Test Coverage Hotspots
| Area | Test Files | Gap |
|------|-----------|-----|
| Backtesting adapters | 0 | **Critical** — 3 adapters, 0 tests |
| Orchestrator | 0 | Integration test missing |
| WorldMonitor | 0 | No validation of macro snapshot |
| LEAN strategy | 0 | Stub only |

---

## Dead Code & Unused Files

- `src/utils/__init__.py` — Empty, no utility functions extracted yet.
- `src/portfolio/backtest.py` — Thin wrapper, mostly pass-through to LEAN stub.
- `src/portfolio/lean_strategy.py` — Stub body with hardcoded dates/cash; not wired to orchestrator.

---

## Skipped Files

None — all 45 Python files in the project were readable and analyzed.

---

## Top 5 Recommendations

1. **Fix all P1 dict key access crashes.** Replace `dict["key"]` with `dict.get("key")` or add validation in `signals.py`, `sentiment.py`, `pybroker_adapter.py`, `lean_strategy.py`. These will crash in production on malformed API responses.

2. **Eliminate bare `except Exception:` anti-pattern.** 14 files swallow errors silently. Replace with specific exception types (`requests.HTTPError`, `ValueError`, `KeyError`) and always log the full traceback before returning fallbacks.

3. **Add tests for backtesting adapters.** VectorBT, Backtrader, and PyBroker adapters have zero test coverage. At minimum, test signal-to-trade mapping, empty-signal handling, and metrics extraction with mocked price data.

4. **Centralize magic numbers.** Create `src/utils/constants.py` for trading-day counts, VIX thresholds, position limits, hold periods, and default cash. Reduces 38 P3 findings to one config file.

5. **Wire WorldMonitor macro context into pipeline.** VIX multiplier and sector momentum are computed but never applied in the orchestrator. Add a `MacroContext` step between scoring and risk agent.
