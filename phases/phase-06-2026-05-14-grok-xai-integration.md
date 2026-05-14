# Phase 6 — Grok / xAI Integration

**Date:** 2026-05-14
**Status:** Complete
**API:** xAI Grok (`api.x.ai`) — OpenAI-compatible

---

## What Phase 6 Adds

Grok models have **native real-time X/Twitter search** built in. Phase 6 makes this Tier 0 in
the sentiment pipeline — the first and highest-priority source, ahead of Polygon and Alpha Vantage.
It also injects politician X activity as context for the Claude decision agent.

---

## Three Changes

### 1. `src/ingestion/xsocial.py` — NEW

OpenAI-compatible client pointed at `https://api.x.ai/v1`.

| Function | Model | What it does |
|----------|-------|-------------|
| `get_x_sentiment(ticker)` | `grok-3-mini` | Search X for recent posts, return `{label, score, articles, source, themes}` |
| `get_politician_x_activity(politician, ticker)` | `grok-3-mini` | Find X posts by/about congress member for ticker, return 2-3 sentence summary |
| `get_market_narrative(ticker)` | `grok-2-latest` | Deep X narrative synthesis (for `--deep-analysis` mode) |

All functions guard on `_KEY = os.getenv("GROK_API_KEY", "")` — silent skip if key absent.

### 2. `src/analysis/sentiment.py` — TIER 0 ADDED

```
Tier 0: Grok/X  ← NEW   (real-time, unlimited, X-native)
Tier 1: Massive/Polygon  (2h cache, free)
Tier 2: Alpha Vantage    (25 calls/day)
Tier 3: Neutral fallback (pipeline never crashes)
```

Return dict gains `"themes": [...]` when `source == "grok_x"`.

### 3. `src/agents/decision_agent.py` + `orchestrator.py` — GROK CONTEXT BLOCK

- `get_recommendation()` gains `grok_context: str = ""` parameter
- Orchestrator pre-fetches `get_politician_x_activity()` per trade
- X themes from Tier 0 sentiment + politician X activity combined into `grok_context` block
- Injected into Claude prompt alongside geo/macro/fundamentals/technicals

Example Claude prompt injection:
```
X/Social Intelligence (NVDA):
  Key X Themes: AI rally, CUDA demand, data center capex
  Politician X Activity: Pelosi tweeted support for CHIPS Act funding on May 10.
  No direct NVDA mention found.
```

---

## Files Changed

| File | Action |
|------|--------|
| `src/ingestion/xsocial.py` | NEW |
| `src/analysis/sentiment.py` | Tier 0 added (18 lines) |
| `src/agents/decision_agent.py` | `grok_context` param + injection |
| `src/agents/orchestrator.py` | Grok pre-fetch in recommendation loop |
| `requirements.txt` | `openai>=1.0.0` added |
| `.env` | `GROK_API_KEY` added |
| `.env.example` | `GROK_API_KEY` documented |
| `tests/unit/test_xsocial.py` | NEW — 7 unit tests |
| `tests/unit/test_sentiment.py` | Tier 0 test + existing tests patched |

---

## xAI API Details

- Base URL: `https://api.x.ai/v1`
- SDK: `openai` Python package (OpenAI-compatible, same format)
- Fast model: `grok-3-mini` — used for sentiment + politician lookup
- Deep model: `grok-2-latest` — used for market narrative
- X search: built into Grok — no extra API parameters needed

---

## Security Note

The API key was shared in plaintext during setup. **Rotate it immediately** at
`console.x.ai → API Keys → Regenerate`. Add the new key to `.env`.

---

## Phase 7 Candidates

- `--grok-deep` flag: run `get_market_narrative()` per ticker and include in Claude prompt
- Save Grok narratives to `data/memos/{ticker}/grok-YYYY-MM-DD.txt` for accumulation
- Use Grok for Lynch Pitch / Munger Invert instead of Claude (cheaper per call)
- Monitor X posts of specific congress members in real-time via scheduled `daily_run.py`
