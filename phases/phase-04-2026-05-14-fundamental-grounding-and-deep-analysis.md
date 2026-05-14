# Phase 4 — Fundamental Grounding & Deep Analysis

**Date:** 2026-05-14
**Status:** Complete
**Inspired by:** Lynch/Munger equity analyst framework (5-step methodology from images)

---

## What Phase 4 Adds

The first three phases built the political alpha pipeline:
- Phase 0: Foundation & research
- Phase 1: Congressional ingestion + decision agent
- Phase 2: Backtesting engine
- Phase 3: WorldMonitor macro context

Phase 4 upgrades the **decision agent** from a pure signal-scoring machine into a
grounded equity analyst that reasons from actual financial evidence — not just scores.

---

## Three Upgrades

### Upgrade 1 — Citation-Disciplined SYSTEM_PROMPT

**What changed:** `src/agents/decision_agent.py` — `SYSTEM_PROMPT`

**Before:** Claude produced reasoning with no sourcing rules.
Hallucinated committee influence, sector momentum, analyst consensus.

**After:** Three mandatory rules enforced in every response:

1. **SOURCE DISCIPLINE** — every factual claim must cite the exact input value.
   Format: `[Source]: "exact value" → interpretation`
   If data missing: state "Not provided in inputs."

2. **DATA RECENCY** — flag stale signals explicitly with recency_weight context.

3. **TRANSPARENCY** — mark inferences as `(inferred from [source])`.

**Why it matters:** Our decision agent now reasons the same way as the 5-step analyst
framework — quote first, interpret second, never guess.

---

### Upgrade 2 — Fundamentals Context Injection

**New file:** `src/analysis/fundamentals.py`

**What it does:** Before every Claude recommendation call, fetches in parallel:
- TTM Income Statement (revenue, gross profit, net income, EPS, YoY growth)
- Annual Balance Sheet (cash, long-term debt, net cash position, equity)
- 5 most recent SEC filings (10-K, 10-Q, 8-K with dates and descriptions)

Source: Financial Datasets API (`financialdatasets.ai`) — already wired as MCP server.
Falls back silently if API key not set or endpoint unavailable.

**Pipeline change:** `get_recommendation()` now accepts `fundamentals: str` parameter.
Orchestrator fetches context per ticker before the Claude call and injects it.

```python
fundamentals = get_fundamentals_context(ticker)
result = get_recommendation(trade, wm_context=wm_ctx, fundamentals=fundamentals)
```

**Why it matters:** Phase 3's framework (Step 3) says upload 5 years of filings.
We replicate that automatically — no manual uploads needed.

---

### Upgrade 3 — Lynch Pitch + Munger Invert (Deep Analysis Mode)

**What changed:** `src/agents/decision_agent.py` — new function `get_deep_analysis()`

**Two new prompts:**
- `LYNCH_PITCH_PROMPT` — "Why would I own this?" — 8-question pitch grounded in signal + fundamentals
- `MUNGER_INVERT_PROMPT` — "How could I lose money?" — 8-question bear case to invalidate the bull

**CLI trigger:**
```bash
python src/agents/orchestrator.py --deep-analysis             # both Lynch + Munger
python src/agents/orchestrator.py --deep-analysis --deep-mode lynch
python src/agents/orchestrator.py --deep-analysis --deep-mode munger
```

**Output:** After each BUY/SELL/HOLD recommendation, prints:
- Lynch Pitch (green section) — the bull thesis with sourced claims
- Munger Invert (red section) — the bear case to stress-test the thesis

**Why it matters:** Phase 4's framework (Step 4) calls these "anchor memos you can reread
in 90 seconds to reset your thinking." Running both eliminates confirmation bias in
the agent's reasoning before trade execution.

---

## Files Changed

| File | Change |
|------|--------|
| `src/analysis/fundamentals.py` | NEW — parallel fetch of income/balance/SEC filings |
| `src/agents/decision_agent.py` | Enhanced SYSTEM_PROMPT (citation rules), fundamentals param, `get_deep_analysis()`, Lynch + Munger prompts |
| `src/agents/orchestrator.py` | Fundamentals fetched per ticker pre-Claude call; `--deep-analysis` / `--deep-mode` flags |

---

## How to Run

**Standard run (Phase 4 fundamentals auto-injected):**
```bash
python src/agents/orchestrator.py --days 90 --top 5
```

**Dry run (scoring only, no Claude):**
```bash
python src/agents/orchestrator.py --dry-run
```

**Full deep analysis (Lynch + Munger per ticker):**
```bash
python src/agents/orchestrator.py --deep-analysis
```

**Single lens:**
```bash
python src/agents/orchestrator.py --deep-analysis --deep-mode munger
```

---

## What Phase 5 Could Be

- **Scheduled quarterly update** — automatically fetch new 10-K/10-Q filings
  when earnings season hits, re-run Lynch/Munger memos, update Obsidian wiki
- **Analyst memo storage** — save Lynch/Munger outputs to `data/memos/{ticker}/`
  so they accumulate over time (the framework says "context compounds")
- **Backtesting with fundamentals filter** — only backtest signals where
  balance sheet health meets minimum criteria (net cash positive, debt/equity < 1)
- **FINANCIAL_DATASETS_API_KEY** — get a real key from financialdatasets.ai
  to unlock income statement, balance sheet, and SEC filing data
