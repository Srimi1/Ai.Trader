# Phase 00: Foundation & Research

- **Date**: 2026-05-13
- **Slug**: foundation-and-research

## Goal

Build the knowledge base. Curate and catalog the top open-source AI trading repositories, frameworks, research papers, and tools. This phase establishes the "north star" — everything we build next is chosen from this curated list.

## Changes

### Research Deliverable

Compiled `ai_trading_repositories.docx` — a curated list of 30+ top-ranked repositories across 6 categories:

#### 1. Frameworks & Trading Engines (Multi-Asset)
| Repository | Stars | Best For | Key Strength |
|------------|-------|----------|--------------|
| [CCXT](https://github.com/ccxt/ccxt) | 39K | Exchange APIs | 100+ exchange support |
| [Freqtrade](https://github.com/freqtrade/freqtrade) | 50K | Crypto trading | ML integration, active community |
| [Zipline](https://github.com/quantopian/zipline) | 19.7K | Academic research | Institutional-grade backtesting |
| [Backtrader](https://github.com/mementum/backtrader) | 20.4K | General backtesting | Extensive indicators |
| [QuantConnect LEAN](https://github.com/QuantConnect/Lean) | 12K | Production trading | Cloud-native, $45B volume |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | 2K+ | High-frequency | Rust core, fastest open-source engine |

#### 2. AI/ML-Specific Trading Systems
| Repository | Stars | Best For | Key Strength |
|------------|-------|----------|--------------|
| [AI-Trader (HKUDS)](https://github.com/HKUDS/AI-Trader) | 1K+ | Autonomous AI | 100% automated LLM agents |
| [FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 10K | RL research | Pre-trained DRL models |
| [FinRL-Trading / FinRL-X](https://github.com/AI4Finance-Foundation/FinRL-Trading) | 3.2K | Modular infra | Next-gen LLM & agentic AI framework |
| [Machine Learning for Trading](https://github.com/stefan-jansen/machine-learning-for-trading) | 14K | ML education | 150+ practical notebooks |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | 200+ | Multi-agent LLM | Simulates hedge fund collaboration |
| [FinGPT](https://github.com/ai4finance-foundation/fingpt) | 2.5K | Financial LLM | MIT license, commercial use |

#### 3. Reinforcement Learning Trading
- PPO, A2C, DDPG, SAC, TD3 agents with realistic trading environments
- Ensemble strategies (ICAIF 2020 research)
- Net unrealized profit as reward function

#### 4. Backtesting & Analysis Tools
| Repository | Stars | Best For | Key Strength |
|------------|-------|----------|--------------|
| [VectorBT](https://github.com/polakowo/vectorbt) | 7.4K | Fast backtesting | Vectorized speed |
| [PyBroker](https://github.com/edtechre/pybroker) | 2K | ML-focused | Walk-forward optimization |
| [Jesse](https://github.com/jesse-ai/jesse) | 6.9K | Crypto AI | AI-powered strategy optimization |

#### 5. Specialized Trading Bots
- **Hummingbot** — Market-making & arbitrage (14K stars)
- **OctoBot** — User-friendly crypto bot (4.7K stars)
- **Zerodha Live Automate Trading** — Indian stock market AI/ML

#### 6. Research Papers & Hugging Face Resources
- [AI-Trader Paper](https://arxiv.org/abs/2512.10971) — Benchmarking autonomous agents in real-time markets
- [TradingAgents Paper](https://huggingface.co/papers/2412.20138) — Multi-agent LLM financial trading framework
- [FinGPT Models on Hugging Face](https://huggingface.co/FinGPT)
- [Trading-Hero-LLM](https://huggingface.co/fuchenru/Trading-Hero-LLM) — 90.8% accuracy FinBERT model

---

## Verification

- [x] Curated 30+ repositories across 6 categories
- [x] Verified all links are active (May 13, 2026)
- [x] Documented star counts, use cases, and key strengths
- [x] Identified top recommendations by use case (autonomous AI, decision support, US stocks)

## Limits

> ⚠️ This is a static snapshot. Repository star counts and activity will change. Some repositories may add breaking changes. We will re-evaluate choices at the start of each phase.

- No code was written in this phase — purely research
- No hands-on evaluation of repositories yet — selection is based on community metrics and documentation quality
- Production readiness of each repo is assumed, not verified

## Follow-ups

- **Phase 1**: Pick exchange API (CCXT) and data source; scaffold project
- **Phase 2**: Evaluate 2–3 backtesting engines hands-on; pick one
- **Phase 3**: Run FinRL tutorial notebooks; understand DRL trading environment
- **Phase 4**: Test AI-Trader autonomous agent on paper trading
- **Phase 5**: Integrate live broker (likely Alpaca or Interactive Brokers via LEAN)
- **Phase 6**: Stress-test with walk-forward validation and paper trading

---

## Roadmap

| Phase | Name | Focus | Key Repositories |
|-------|------|-------|------------------|
| 1 | Foundation | Data ingestion, exchange APIs, project scaffolding | CCXT, custom data pipeline |
| 2 | Backtesting Engine | Strategy validation, historical simulation | Backtrader, VectorBT, Zipline |
| 3 | ML/RL Strategies | Supervised & reinforcement learning models | FinRL, PyBroker, ML4T |
| 4 | AI Agent Layer | LLM agents for decision support & reasoning | AI-Trader, TradingAgents, FinGPT |
| 5 | Live Execution | Production trading, risk management, broker integration | LEAN, NautilusTrader |
| 6 | Optimization & Scale | Performance tuning, walk-forward validation, multi-asset | VectorBT, PyBroker, custom |

> **Motivation**: Phase 0 is done. We have the map. Phase 1 starts now.
