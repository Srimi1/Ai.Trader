#!/bin/bash

# =====================================================
# AI Trading Repositories Auto-Clone Script
# Generated: May 13, 2026
# =====================================================

ROOT="ai-trading-repos"
REPORT="$ROOT/clone_report.txt"
SUCCESS=0
FAILED=0

mkdir -p "$ROOT"
echo "AI Trading Repos Clone Report - $(date)" > "$REPORT"
echo "=======================================" >> "$REPORT"

clone_repo() {
  local DIR="$1"
  local URL="$2"
  local NAME=$(basename "$URL" .git)
  mkdir -p "$ROOT/$DIR"
  echo -n "Cloning $NAME ... "
  if git clone --depth=1 "$URL" "$ROOT/$DIR/$NAME" >> "$REPORT" 2>&1; then
    echo "✅ Done"
    echo "SUCCESS: $NAME" >> "$REPORT"
    ((SUCCESS++))
  else
    echo "❌ Failed"
    echo "FAILED: $NAME" >> "$REPORT"
    ((FAILED++))
  fi
}

# ─── 1. INSTITUTIONAL FRAMEWORKS ─────────────────────
echo ""
echo "📦 Section 1: Institutional & Professional Frameworks"
clone_repo "01_institutional_frameworks" "https://github.com/microsoft/qlib"
clone_repo "01_institutional_frameworks" "https://github.com/vnpy/vnpy"
clone_repo "01_institutional_frameworks" "https://github.com/goldmansachs/gs-quant"
clone_repo "01_institutional_frameworks" "https://github.com/QuantConnect/Lean"
clone_repo "01_institutional_frameworks" "https://github.com/nautechsystems/nautilus_trader"

# ─── 2. AI/ML AUTONOMOUS AGENTS ──────────────────────
echo ""
echo "🤖 Section 2: AI/ML Trading Systems & Autonomous Agents"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/HKUDS/AI-Trader"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/AI4Finance-Foundation/FinRL"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/AI4Finance-Foundation/FinRL-Trading"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/stefan-jansen/machine-learning-for-trading"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/TauricResearch/TradingAgents"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/ai4finance-foundation/fingpt"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/je-suis-tm/quant-trading"
clone_repo "02_ai_ml_autonomous_agents" "https://github.com/LLMQuant/SentimentGPT"

# ─── 3. DEEP LEARNING ────────────────────────────────
echo ""
echo "🧠 Section 3: Deep Learning for Trading"
clone_repo "03_deep_learning_trading" "https://github.com/034adarsh/Stock-Price-Prediction-Using-LSTM"
clone_repo "03_deep_learning_trading" "https://github.com/virajbhutada/google-stock-price-forecasting-lstm"
clone_repo "03_deep_learning_trading" "https://github.com/sinanw/lstm-stock-price-prediction"
clone_repo "03_deep_learning_trading" "https://github.com/TheQuantScientist/CNN-LSTM-AM"
clone_repo "03_deep_learning_trading" "https://github.com/zanuura/deep_learning_stock_prediction"
clone_repo "03_deep_learning_trading" "https://github.com/Rachnog/Deep-Trading"
clone_repo "03_deep_learning_trading" "https://github.com/ebrahimpichka/DeepRL-trade"

# ─── 4. REINFORCEMENT LEARNING ───────────────────────
echo ""
echo "🎮 Section 4: Reinforcement Learning Trading"
clone_repo "04_reinforcement_learning" "https://github.com/theanh97/Deep-Reinforcement-Learning-with-Stock-Trading"
clone_repo "04_reinforcement_learning" "https://github.com/Albert-Z-Guo/Deep-Reinforcement-Stock-Trading"
clone_repo "04_reinforcement_learning" "https://github.com/Jung132914/Deep-Reinforcement-Learning-for-Automated-Stock-Trading-Ensemble-Strategy-ICAIF-2020"
clone_repo "04_reinforcement_learning" "https://github.com/alextmn/rf-trading-bot"
clone_repo "04_reinforcement_learning" "https://github.com/pythonlessons/RL-Bitcoin-trading-bot"
clone_repo "04_reinforcement_learning" "https://github.com/krish-sky1ark/Portfolio-Optimisation-Using-Deep-Reinforcement-Learning"
clone_repo "04_reinforcement_learning" "https://github.com/Amey-Thakur/OPTIMIZING-STOCK-TRADING-STRATEGY-WITH-REINFORCEMENT-LEARNING"

# ─── 5. PORTFOLIO OPTIMIZATION ───────────────────────
echo ""
echo "📊 Section 5: Portfolio Optimization & Risk Management"
clone_repo "05_portfolio_optimization" "https://github.com/jankrepl/deepdow"
clone_repo "05_portfolio_optimization" "https://github.com/AnnaSkarpalezou/Portfolio-Optimization-using-Machine-Learning"
clone_repo "05_portfolio_optimization" "https://github.com/Gouldh/ML-Portfolio-Optimization"
clone_repo "05_portfolio_optimization" "https://github.com/ranaroussi/quantstats"
clone_repo "05_portfolio_optimization" "https://github.com/skfolio/skfolio"

# ─── 6. SENTIMENT & NLP ──────────────────────────────
echo ""
echo "💬 Section 6: Sentiment Analysis & NLP for Trading"
clone_repo "06_sentiment_nlp" "https://github.com/risabhmishra/algotrading-sentimentanalysis-genai"
clone_repo "06_sentiment_nlp" "https://github.com/shirosaidev/stocksight"
clone_repo "06_sentiment_nlp" "https://github.com/dshilman/stock-sentiment-analysis"
clone_repo "06_sentiment_nlp" "https://github.com/gandalf1819/Stock-Market-Sentiment-Analysis"
clone_repo "06_sentiment_nlp" "https://github.com/rishikonapure/Cryptocurrency-Sentiment-Analysis"

# ─── 7. OPTIONS & VOLATILITY ─────────────────────────
echo ""
echo "📈 Section 7: Options Trading & Volatility Strategies"
clone_repo "07_options_volatility" "https://github.com/pranav6226/Option_Price_Prediction"
clone_repo "07_options_volatility" "https://github.com/devxinvestor/Options"
clone_repo "07_options_volatility" "https://github.com/nataliaburrey/Options_Trading_ML"
clone_repo "07_options_volatility" "https://github.com/PyPatel/Options-Trading-Strategies-in-Python"
clone_repo "07_options_volatility" "https://github.com/anthonymakarewicz/volatility-trading"

# ─── 8. PAIRS TRADING ────────────────────────────────
echo ""
echo "🔁 Section 8: Pairs Trading & Statistical Arbitrage"
clone_repo "08_pairs_trading_arbitrage" "https://github.com/omarequalmars/Pairs-Trading-Tutorial"
clone_repo "08_pairs_trading_arbitrage" "https://github.com/Xinyi6/Pairs-Trading"
clone_repo "08_pairs_trading_arbitrage" "https://github.com/coderaashir/Crypto-Pairs-Trading"
clone_repo "08_pairs_trading_arbitrage" "https://github.com/anthonyli01/Statistical-Arbitrage-Pairs-Trading-Strategy"

# ─── 9. TECHNICAL ANALYSIS ───────────────────────────
echo ""
echo "📉 Section 9: Technical Analysis Libraries"
clone_repo "09_technical_analysis" "https://github.com/TA-Lib/ta-lib-python"
clone_repo "09_technical_analysis" "https://github.com/bukosabino/ta"
clone_repo "09_technical_analysis" "https://github.com/Nikhil-Adithyan/Algorithmic-Trading-with-Python"

# ─── 10. BACKTESTING ─────────────────────────────────
echo ""
echo "⏮ Section 10: Backtesting Frameworks"
clone_repo "10_backtesting_frameworks" "https://github.com/quantopian/zipline"
clone_repo "10_backtesting_frameworks" "https://github.com/mementum/backtrader"
clone_repo "10_backtesting_frameworks" "https://github.com/polakowo/vectorbt"
clone_repo "10_backtesting_frameworks" "https://github.com/edtechre/pybroker"
clone_repo "10_backtesting_frameworks" "https://github.com/kernc/backtesting.py"

# ─── 11. CRYPTO BOTS ─────────────────────────────────
echo ""
echo "🪙 Section 11: Crypto Trading Bots"
clone_repo "11_crypto_bots" "https://github.com/freqtrade/freqtrade"
clone_repo "11_crypto_bots" "https://github.com/jesse-ai/jesse"
clone_repo "11_crypto_bots" "https://github.com/hummingbot/hummingbot"
clone_repo "11_crypto_bots" "https://github.com/Drakkar-Software/OctoBot"
clone_repo "11_crypto_bots" "https://github.com/ccxt/ccxt"
clone_repo "11_crypto_bots" "https://github.com/ilcardella/TradingBot"

# ─── 12. SPECIALIZED STRATEGIES ──────────────────────
echo ""
echo "🎯 Section 12: Specialized Strategies"
clone_repo "12_specialized_strategies" "https://github.com/lpiekarski/algo-trading"
clone_repo "12_specialized_strategies" "https://github.com/LastAncientOne/Stock_Analysis_For_Quant"
clone_repo "12_specialized_strategies" "https://github.com/LastAncientOne/Deep_Learning_Machine_Learning_Stock"
clone_repo "12_specialized_strategies" "https://github.com/robertmartin8/MachineLearningStocks"
clone_repo "12_specialized_strategies" "https://github.com/keyvantaj/Quantitative"
clone_repo "12_specialized_strategies" "https://github.com/merovinh/best-of-algorithmic-trading"
clone_repo "12_specialized_strategies" "https://github.com/wilsonfreitas/awesome-quant"
clone_repo "12_specialized_strategies" "https://github.com/leoncuhk/awesome-quant-ai"
clone_repo "12_specialized_strategies" "https://github.com/yugeshk/Zerodha_Live_Automate_Trading-_using_AI_ML_on_Indian_stock_market"

# ─── SUMMARY ─────────────────────────────────────────
echo ""
echo "========================================"
echo "✅ Clone complete!"
echo "   Succeeded : $SUCCESS"
echo "   Failed    : $FAILED"
echo "   Report    : $REPORT"
echo "========================================"
echo "" >> "$REPORT"
echo "Total: $SUCCESS succeeded, $FAILED failed" >> "$REPORT"
