# Audit Report — AI.Trader — 2026-05-13

## Executive Summary

| Metric | Count |
|--------|-------|
| Files scanned | 46 |
| P1 Critical (crash / security / data-loss) | 33 |
| P2 Warnings (logic / error-handling) | 72 |
| P3 Nits (style / completeness) | 22 |
| **Total findings** | **127** |
| Secrets / API keys leaked on GitHub | **0** |
| PII leaked on GitHub | **0** (1 path disclosure fixed) |
| Test coverage | Unit: 96 pass · Integration: 19 pass |

**GitHub status:** Clean. `.mcp.json` hardcoded local path (`/Volumes/Srimi Drive 1/...`) was found and removed in commit `88dfad2`, pushed to `main`.

---

## GitHub / Secrets Scan Results

| Check | Result |
|-------|--------|
| Real API keys in any git commit | **NONE FOUND** |
| Real API keys in current tree | **NONE FOUND** |
| Personal email in source files | **NONE** (git commit metadata only — normal) |
| Phone / personal data | **NONE FOUND** |
| Hardcoded local path `/Volumes/Srimi Drive 1/...` | **FIXED** — commit `88dfad2` |
| `.env` file committed | **NO** — correctly gitignored |
| `.env.example` | **SAFE** — placeholders only (`your_key_here`) |
| `AI-Trader/` and `ai-trading-repos/` | **NOT in repo** — gitignored |

---

## P1 — Critical Issues (33)

### Security

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/mcp/financial_datasets.py` | 43 | URL parameter injection — ticker/period etc. interpolated into f-string URLs. `ticker='AAPL&limit=9999'` bypasses limits. | Use `httpx` `params={}` dict |
| `src/mcp/financial_datasets.py` | 22 | Unauthenticated requests silently sent when key absent; 401 swallowed | Warn at startup if key missing |
| `requirements.txt` | 1 | `mcp` and `httpx` missing — MCP server crashes on import in clean venv | Add to `requirements-mcp.txt` |

### Crashes — Agents

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/agents/decision_agent.py` | 31 | `os.environ['ANTHROPIC_API_KEY']` raises `KeyError` if unset | `os.getenv()` + explicit check |
| `src/agents/decision_agent.py` | 39 | 6 bare `trade['key']` in f-string — any missing key aborts Claude call | `.get()` with defaults |
| `src/agents/decision_agent.py` | 63 | `message.content[0].text` — `IndexError` on blocked/empty response | Guard `if not message.content` |
| `src/agents/orchestrator.py` | 105 | `t['sentiment']['label']` bare access — `KeyError` if sentiment skipped | `.get('sentiment', {}).get('label', 'N/A')` |
| `src/agents/risk_agent.py` | 12 | `trade['transaction_date']` bare access in `_disclosure_lag` | `.get('transaction_date', '')` |

### Crashes — Ingestion

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/ingestion/congress.py` | 86 | `_load_cache()` no error handling — corrupted JSON crashes pipeline | `try/except (JSONDecodeError, OSError): return []` |
| `src/ingestion/congress.py` | 91 | `_save_cache()` non-atomic — disk-full mid-write corrupts cache | Write to tempfile, `os.replace()` |
| `src/ingestion/news.py` | 43 | `float()` on AV empty-string field — `ValueError` | `_safe_float()` helper |
| `src/ingestion/news.py` | 26 | AV rate-limit body (`{"Note":...}`) not detected — corrupt data flows downstream | Check `Note`/`Information` keys post-`.json()` |
| `src/ingestion/prices.py` | 35 | Silent `except Exception: return None` masks `close` column absence | Log before returning |
| `src/ingestion/worldmonitor.py` | 34 | All 5 file loaders have no error handling — missing submodule crashes app | `try/except (FileNotFoundError, JSONDecodeError)` |

### Crashes — Analysis

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/analysis/signals.py` | 10 | `CONFIG` loaded at import with no error handling | `try/except`, raise `ConfigurationError` |
| `src/analysis/signals.py` | 13 | Bare `CONFIG['amount_weights']` at module level — `KeyError` on schema change | `.get()` + validate required keys |

### Crashes — Backtesting

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `src/backtesting/metrics.py` | 27 | Zero-peak division in `max_drawdown` if starting equity is 0 | Guard `if (peak == 0).any(): return 0.0` |
| `src/backtesting/metrics.py` | 68 | Negative `end_value` → `ValueError` from fractional exponent on negative base | Guard `if end_value <= 0: return -1.0` |
| `src/backtesting/walkforward.py` | 29 | `strptime` crash on bad date kills entire walk-forward run | `try/except ValueError: continue` |
| `src/backtesting/benchmark.py` | 10 | `ZeroDivisionError` / multi-index scalar in SPY benchmark | Guard division, normalize columns |
| `src/backtesting/adapters/vectorbt_adapter.py` | 55 | Missing `Close` column check before access | `if 'Close' not in df.columns: raise ValueError` |
| `src/backtesting/adapters/vectorbt_adapter.py` | 85 | `get_loc` fails on duplicate index | Deduplicate index |
| `src/backtesting/adapters/backtrader_adapter.py` | 29 | `strptime` in `next()` — one bad date stops entire backtest | `try/except ValueError: return` |
| `src/backtesting/adapters/backtrader_adapter.py` | 134 | Bare `except` swallows all feed errors silently | Catch specific, log, re-raise |
| `src/backtesting/adapters/backtrader_adapter.py` | 178 | `NameError: close_vals` when `spy.empty` | `if spy.empty: return` before assignment |
| `src/backtesting/adapters/pybroker_adapter.py` | 109 | `except Exception: pass` on benchmark fetch — silent failure | Log and surface |
| `src/portfolio/backtest.py` | 44 | `subprocess.run` no error handling — `CalledProcessError` unhandled | `try/except CalledProcessError` |

---

## P2 — Warnings (72, top issues listed)

### Logic Errors

| File | Line | Issue |
|------|------|-------|
| `src/ingestion/congress.py` | 166 | `normalize()` maps `Party` (D/R) to field named `district` — semantic mismatch |
| `src/ingestion/news.py` | 54 | Averages include zero-scored articles where ticker absent → neutral bias |
| `src/ingestion/prices.py` | 34 | Returns last available price in 6-day window; no indication of actual date used |
| `src/ingestion/prices.py` | 45 | `if start_price and exit_price` treats `0.0` as `None` |
| `src/analysis/signals.py` | 45 | `_cluster_bonus` counts the scored trade in its own cluster (inflates by 1) |
| `src/analysis/signals.py` | 72 | `sale_partial` in signal list but `congress.py` never produces it — dead branch |
| `src/analysis/sentiment.py` | 19 | `EnvironmentError` (missing AV key) caught silently → all tickers neutral |
| `src/agents/orchestrator.py` | 103 | `t['adjusted_score']` bare access — `KeyError` if sentiment layer skipped |
| `src/agents/risk_agent.py` | 40 | `position_size(0.0)` returns silent 0% — no guard against zero score |
| `src/portfolio/lean_strategy.py` | 54 | No aggregate allocation cap — 20+ same-day BUYs → >100% allocated |
| `src/portfolio/lean_strategy.py` | 50 | `AddEquity` called every tick on existing tickers → duplicate subscriptions |
| `src/portfolio/lean_strategy.py` | 21 | `SetEndDate(2025, 12, 31)` now in past — excludes 2026 data |
| `config/politicians.json` | 29 | Amount weight keys use `$X-$Y` (no spaces) vs Quiver data `$X - $Y` → all lookups fall to default `0.8` |
| `src/backtesting/adapters/backtrader_adapter.py` | 206 | `get_trades()` always returns `[]` — trade log never populated |
| `src/backtesting/walkforward.py` | 49 | Train window bleeds into test window — look-ahead bias |
| `src/backtesting/report.py` | 117 | `chart_path` unsanitised in HTML output |
| `tests/fixtures/sample_trades.py` | 16 | `disclosure_date` can precede `transaction_date` when `days_ago <= 3` |

### Dependencies

| File | Line | Issue |
|------|------|-------|
| `requirements.txt` | 13 | `lib-pybroker` wrong PyPI name — should be `pybroker` |
| `requirements.txt` | 14 | `backtrader` unmaintained since 2021 — incompatible with pandas 2.x |
| `requirements.txt` | 9 | `torch`/`transformers` unpinned — CVE exposure |

---

## P3 — Nits (22, key items)

| File | Line | Issue |
|------|------|-------|
| `src/analysis/signals.py` | 84 | BUY/SELL thresholds (0.5/-0.5) duplicated in `sentiment.py` — will drift |
| `src/analysis/macro.py` | 18 | `_SECTOR_MOMENTUM_THRESHOLDS` defined but never used — dead code |
| `src/ingestion/worldmonitor.py` | 24 | `warnings.filterwarnings('ignore')` at module level silences ALL warnings |
| `tests/fixtures/sample_trades.py` | 19 | Real BioGuideID `P000197` (Nancy Pelosi) — use synthetic `TEST000001` |
| `tests/unit/test_metrics.py` | 96 | `profit_factor(all wins) == 0.0` — should be `float('inf')` |
| `src/agents/orchestrator.py` | 118 | Step counter `[4/4]` wrong — pipeline has 5 steps |
| `src/portfolio/lean_strategy.py` | 37 | `dict[str, datetime]` annotation wrong — keys are LEAN `Symbol` objects |
| `src/mcp/financial_datasets.py` | 128 | `str \| None` syntax; Python 3.10+. Runs in 3.11 venv but add `from __future__ import annotations` |

---

## Top 10 Recommendations

1. **Fix `decision_agent.py` crash surface** — guard `os.environ[]`, all `trade['key']`, `message.content[0]` (**P1, ~10 lines**)
2. **Fix URL injection in `financial_datasets.py`** — use `params={}` dict (**P1, security**)
3. **Atomic cache writes in `congress.py`** — tempfile + `os.replace()` (**P1, data integrity**)
4. **AV rate-limit detection in `news.py`** — check `Note`/`Information` keys (**P1, silent corruption**)
5. **Fix worldmonitor loaders** — `try/except` in all 5 loaders (**P1, startup safety**)
6. **Fix LEAN over-leverage** — cap aggregate daily allocation in `lean_strategy.py` (**P2, financial risk**)
7. **Fix `requirements.txt`** — `lib-pybroker` → `pybroker` (**P1-equivalent, app won't install**)
8. **Fix `profit_factor` to return `float('inf')`** — current 0.0 semantically wrong (**P3 test, P2 logic**)
9. **Replace `sys.path.insert` hacks** — `pip install -e .` + `conftest.py` (**P2, test reliability**)
10. **Fix fixture disclosure dates** — `disc_date = tx_date + timedelta(days=3)` (**P2, test validity**)
