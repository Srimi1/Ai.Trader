# AI.Trader

An autonomous AI-powered trading system combining institutional frameworks, machine learning agents, and alternative data sources for intelligent market analysis and decision-making.

## 🎯 Project Overview

AI.Trader is a comprehensive trading platform that integrates:
- **Multi-agent AI architecture** for distributed decision-making
- **Alternative data ingestion** (congressional trades, sentiment, news)
- **Multiple backtesting frameworks** (Backtrader, VectorBT, PyBroker)
- **Portfolio optimization** with risk management
- **Real-time signal generation** from macro and sentiment analysis

## 🏗️ Architecture

```
src/
├── agents/          # AI decision-making agents (orchestrator, risk, decision)
├── analysis/        # Signal generation (macro, sentiment, technical)
├── backtesting/     # Multi-framework backtesting engine
├── ingestion/       # Data pipelines (prices, congress, news, worldmonitor)
├── portfolio/       # Portfolio management and optimization
├── mcp/             # Model Context Protocol integrations
└── utils/           # Shared utilities
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/Srimi1/Ai.Trader.git
cd Ai.Trader

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: ANTHROPIC_API_KEY, ALPHA_VANTAGE_KEY
# Optional: QUIVER_QUANT_KEY, FINANCIAL_DATASETS_API_KEY
```

## 📊 Features

### Data Ingestion
- **Market Data**: Alpha Vantage, Polygon.io integration
- **Alternative Data**: Congressional trades, insider transactions
- **Sentiment Analysis**: News and social media sentiment
- **Macro Indicators**: Economic data and global events

### AI Agents
- **Orchestrator**: Coordinates multi-agent workflows
- **Risk Agent**: Real-time risk assessment and position sizing
- **Decision Agent**: Trade signal generation and execution logic

### Backtesting
- Multi-framework support (Backtrader, VectorBT, PyBroker)
- Walk-forward optimization
- Comprehensive performance metrics
- Automated reporting

### Portfolio Management
- Dynamic position sizing
- Risk-adjusted allocation
- Multi-strategy portfolio optimization

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=src tests/
```

## 📁 Project Structure

- **phases/**: Development roadmap and milestones
- **config/**: Configuration files (politicians list, settings)
- **docs/**: Documentation and guides
- **tests/**: Unit and integration tests
- **scripts/**: Utility scripts

## 🔐 Security

- **Never commit** `.env` files or API keys
- All sensitive data is gitignored
- Use `.env.example` as template
- Review `.gitignore` before committing

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - AI agent interaction guide
- [phases/](phases/) - Development phases and progress
- [config/politicians.json](config/politicians.json) - Tracked politicians for congressional trades

## 🛠️ Development

### Phase 0: Foundation (Current)
- ✅ Project structure setup
- ✅ Data ingestion pipelines
- ✅ Multi-agent architecture
- ✅ Backtesting framework integration
- 🔄 Alternative data source integration

See [phases/phase-00-2026-05-13-foundation-and-research.md](phases/phase-00-2026-05-13-foundation-and-research.md) for details.

## 🤝 Contributing

This is a personal research project. For questions or suggestions, please open an issue.

## 📄 License

Private research project - All rights reserved.

## 🔗 Related Resources

- [Quiver Quant Alternatives Guide](docs/) - Alternative data sources
- [AI Trading Repositories](clone_ai_trading.sh) - Research repository collection script

## ⚠️ Disclaimer

This software is for educational and research purposes only. Not financial advice. Trading involves substantial risk of loss. Always do your own research and consult with financial professionals before making investment decisions.

---

**Built with**: Python, Anthropic Claude, Alpha Vantage, Multiple Backtesting Frameworks
