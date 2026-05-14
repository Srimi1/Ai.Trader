# Phases

This directory tracks the AI.Trader project progress phase by phase.

## Convention

- Each phase is a numbered markdown document
- Naming: `phase-NN-YYYY-MM-DD-<slug>.md`
- Phase 0 is the foundation/research phase — already complete
- Phase 1, 2, 3… are the build phases

## How to Save a Phase Snapshot

When you want to capture what we have done in a session, run:

```bash
python ~/.claude/skills/save-phase/scripts/save_phase.py --title "What we did"
```

Or simply say: **"/save"**

This auto-generates the next phase document with:
- Git diff stats
- Untracked files
- Recent commits
- Goal / Changes / Verification / Limits / Follow-ups sections

## Honesty Rules

- **"verified"** = I ran it and saw it work
- **"limits"** = What was NOT tested, what could break
- No false confidence — if something was eyeballed, say so

## Current Status

| Phase | Status | Focus |
|-------|--------|-------|
| Phase 0 | ✅ Complete | Foundation & Research — curated 67 AI trading repositories |
| Phase 1 | ✅ Complete | Infrastructure — data ingestion, Political Trades AI Agent, APIs |
| Phase 2 | ✅ Complete | Backtesting Engine — VectorBT, Backtrader, PyBroker adapters |
| Phase 3 | ✅ Complete | WorldMonitor Integration & Backtesting Hardening |
| Phase 4 | 📋 Planned | ML/RL Strategies — supervised & reinforcement learning models |
| Phase 5 | 📋 Planned | Live Execution — production trading & risk management |
| Phase 6 | 📋 Planned | Optimization & Scale — performance tuning, multi-asset expansion |
