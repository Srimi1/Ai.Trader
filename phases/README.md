# Phases

This directory tracks the AI.Trader project progress phase by phase.

## Convention

- Each phase is a numbered markdown document
- Naming: `phase-NN-YYYY-MM-DD-<slug>.md`
- Phase 0 is the foundation/research phase — already complete
- Phase 1, 2, 3… are the build phases ahead of us

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
| Phase 0 | ✅ Complete | Foundation & Research — curated 30+ AI trading repositories |
| Phase 1 | 🔜 Next | Infrastructure — data ingestion, exchange APIs, project scaffolding |
| Phase 2 | 📋 Planned | Backtesting Engine — strategy validation framework |
| Phase 3 | 📋 Planned | ML/RL Strategies — supervised & reinforcement learning models |
| Phase 4 | 📋 Planned | AI Agent Layer — LLM agents for decision support |
| Phase 5 | 📋 Planned | Live Execution — production trading & risk management |
| Phase 6 | 📋 Planned | Optimization & Scale — performance tuning, multi-asset expansion |
