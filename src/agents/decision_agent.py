"""Claude-powered decision agent: takes scored + sentiment-enriched trade → BUY/HOLD/SELL."""
import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not _API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY not set in .env — decision agent cannot start")

SYSTEM_PROMPT = """You are a US equity trading analyst specializing in political alpha signals.
You analyze congressional stock disclosures (STOCK Act filings) and produce actionable trade recommendations.

OUTPUT FORMAT — MANDATORY. Your response must begin with these exact lines, no preamble:
RECOMMENDATION: [BUY | HOLD | SELL]
CONFIDENCE: [HIGH | MEDIUM | LOW]
POSITION_SIZE: [1-5]% of portfolio
STOP_LOSS: -[X]%
TAKE_PROFIT: +[X]%
REASONING: <2-3 sentences — cite input values using [Source]: "value" → interpretation>
RISK_NOTE: <one sentence — cite specific risk from geo/macro/fundamental data provided>

CITATION RULES (apply inside REASONING and RISK_NOTE):
- Cite every factual claim: [Source]: "exact value" → your interpretation.
  Example: [Signal Score]: "+1.82" → strong congressional conviction.
- Do NOT use general knowledge to fill gaps. If data missing: state "Not in provided inputs."
- Mark inferences: (inferred from [source]).
- Flag stale signals: (Note: recency_weight=X — trade aged X days.)

Inputs you will receive per trade:
- Politician name, ticker, trade type, amount range, transaction/disclosure dates
- Signal score + score components (politician weight, amount weight, recency weight, cluster bonus)
- News sentiment (label, score, article count)
- WorldMonitor Finance geopolitical + market context (when available)
- Fundamental data: income statement, balance sheet, recent SEC filings (when available)
- X/Social Intelligence: real-time X sentiment + politician X activity (when available)"""

LYNCH_PITCH_PROMPT = """You are writing a Lynch-style investment pitch for {ticker}.

TASK: Write a short investment pitch explaining why {ticker} could be a good stock to own.
Use ONLY the fundamental data and signal inputs provided. Every factual claim must cite its source.

Answer in order:
1. In one sentence — what does this company do? [cite: SEC filings if available]
2. The ONE simple reason this political signal suggests a trade. [cite: Signal Score, Politician]
3. How does the company make money? [cite: income statement if available]
4. Balance sheet health today. [cite: balance sheet — cash, debt, net position]
5. What kind of company is this? (slow grower / stalwart / fast grower / cyclical / turnaround)
6. What could go wrong? [cite: Risk Note, geo risk if elevated]
7. Why might the market be missing this?
8. Bottom line — 2-3 sentences: why it's interesting, what must go right, what would prove you wrong.

WRITING STYLE: Plain English. Short sentences. No buzzwords. No valuation models.
If fundamental data is missing, state "Not in provided data" — do not guess."""

MUNGER_INVERT_PROMPT = """You are writing a Munger-style bear case for {ticker}.

TASK: Write a short investment memo that assumes {ticker} is a BAD long-term investment.
Your goal is to invalidate the bull thesis. Use ONLY the inputs provided — cite every claim.

Answer in order:
1. What is the most likely way an investor could lose money here? [cite: signals, geo risk]
2. Where is the business structurally weak? [cite: income/balance sheet if available]
3. What assumptions in the bull case must go right — and might not?
4. What could permanently impair earnings or cash flow? [cite: SEC filings if available]
5. Is the balance sheet a hidden risk? [cite: debt/cash data]
6. How could management hurt shareholders?
7. Why might the political signal be misleading here?
8. What evidence would prove this bear case right?

WRITING STYLE: Direct. Skeptical tone. Short sentences. No buzzwords."""


def _fetch_wm_context(ticker: str) -> dict:
    """
    Fetch geopolitical + macro context for a ticker.
    Uses geo_context.py (Python 3.9 compatible, no mcp dep, sync).
    """
    try:
        from src.analysis.geo_context import get_context_for_ticker
        return get_context_for_ticker(ticker)
    except Exception as e:
        logger.warning("geo_context fetch failed: %s", e)
        return {}


def get_recommendation(trade: dict, wm_context: dict = None, fundamentals: str = "", technicals: str = "", grok_context: str = "") -> dict:
    """
    Args:
        trade: Enriched trade dict from the pipeline.
        wm_context: Pre-fetched WorldMonitor context dict (optional).
        fundamentals: Pre-fetched fundamentals block from get_fundamentals_context() (optional).
        grok_context: Pre-fetched X/social intelligence block from xsocial.py (optional).
    """
    client = anthropic.Anthropic(api_key=_API_KEY, timeout=30.0)

    sentiment = trade.get("sentiment", {})
    components = trade.get("score_components", {})
    score = trade.get("score", 0.0)
    ticker = trade.get("ticker", "N/A")

    # WorldMonitor geopolitical + macro context
    if wm_context is None:
        wm_context = _fetch_wm_context(ticker)

    geo = wm_context.get("geo_risk", {})
    market = wm_context.get("market", {})

    geo_block = ""
    if geo:
        geo_block = f"""
WorldMonitor Finance — Geopolitical Risk ({ticker}):
  Risk Score: {geo.get('risk_score', 'N/A')}/10 ({geo.get('risk_label', 'N/A')})
  Country Exposure: {geo.get('country_exposure', 'US')} — {geo.get('country_note', '')}
  Sector Risk: {geo.get('sector_note', 'N/A')}
  Geo Recommendation: {geo.get('recommendation', 'N/A')}"""

    market_block = ""
    if market:
        macro = market.get("macro_snapshot", {})
        market_block = f"""
WorldMonitor Finance — Market Context:
  Overall Risk: {market.get('overall_market_risk_score', 'N/A')}/10 — {market.get('overall_assessment', '')}
  VIX: {macro.get('vix', 'N/A')} | 10Y Yield: {macro.get('yield_10y', 'N/A')}% | Oil 1d: {macro.get('oil_1d_change_pct', 'N/A')}%
  Risk Flags: {', '.join(market.get('risk_flags', [])) or 'None'}
  Trading Guidance: {market.get('trading_guidance', 'NORMAL sizing')}"""

    user_msg = f"""Congressional Trade Signal:

Politician: {trade.get('representative', 'Unknown')}
Ticker: {ticker}
Trade Type: {(trade.get('trade_type') or 'unknown').upper()}
Amount: {trade.get('amount_range', 'N/A')}
Transaction Date: {trade.get('transaction_date', 'N/A')}
Disclosure Date: {trade.get('disclosure_date', 'N/A')}

Signal Score: {score:+.3f} (adjusted: {trade.get('adjusted_score', score):+.3f})
Score Components:
  - Politician weight: {components.get('politician', 1.0):.2f}
  - Amount weight: {components.get('amount', 1.0):.2f}
  - Recency weight: {components.get('recency', 1.0):.2f}
  - Cluster bonus: {components.get('cluster', 1.0):.2f}

News Sentiment: {sentiment.get('label', 'Unknown')} (score={sentiment.get('score', 0):.3f}, n={sentiment.get('articles', 0)} articles, source={sentiment.get('source', 'unknown')})
{geo_block}{market_block}{technicals}{fundamentals}{grok_context}
Provide your recommendation."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError as e:
        logger.error("Anthropic API error for %s: %s", trade.get("ticker"), e)
        raise

    if not message.content:
        raise RuntimeError(f"Empty response from Anthropic for ticker {trade.get('ticker')}")

    raw = message.content[0].text
    return {"ticker": trade.get("ticker", "N/A"), "raw": raw, "trade": trade}


def get_deep_analysis(trade: dict, fundamentals: str = "", mode: str = "both") -> dict:
    """
    Run Lynch Pitch and/or Munger Invert analysis for a ticker.

    Args:
        trade: Enriched trade dict (same as get_recommendation input).
        fundamentals: Pre-fetched fundamentals block string.
        mode: "lynch" | "munger" | "both"

    Returns:
        {"ticker": str, "lynch_pitch": str|None, "munger_invert": str|None}
    """
    client = anthropic.Anthropic(api_key=_API_KEY, timeout=45.0)
    ticker = trade.get("ticker", "N/A")

    context_block = f"""Signal Inputs:
  Ticker: {ticker}
  Politician: {trade.get('representative', 'Unknown')}
  Trade Type: {(trade.get('trade_type') or 'unknown').upper()}
  Amount: {trade.get('amount_range', 'N/A')}
  Signal Score: {trade.get('score', 0):+.3f} (adjusted: {trade.get('adjusted_score', 0):+.3f})
  Sentiment: {trade.get('sentiment', {}).get('label', 'N/A')} (score={trade.get('sentiment', {}).get('score', 0):.3f})
  Transaction Date: {trade.get('transaction_date', 'N/A')}
{fundamentals}"""

    result = {"ticker": ticker, "lynch_pitch": None, "munger_invert": None}

    if mode in ("lynch", "both"):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": LYNCH_PITCH_PROMPT.format(ticker=ticker) + f"\n\n{context_block}"}],
            )
            result["lynch_pitch"] = msg.content[0].text if msg.content else ""
        except Exception as e:
            logger.error("Lynch Pitch failed for %s: %s", ticker, e)

    if mode in ("munger", "both"):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": MUNGER_INVERT_PROMPT.format(ticker=ticker) + f"\n\n{context_block}"}],
            )
            result["munger_invert"] = msg.content[0].text if msg.content else ""
        except Exception as e:
            logger.error("Munger Invert failed for %s: %s", ticker, e)

    return result


def parse_recommendation(raw: str) -> dict:
    lines = raw.strip().split("\n")
    result = {}
    for line in lines:
        if ":" in line:
            key, _, value = line.partition(":")
            # strip markdown bold/italic markers from Claude responses
            clean_key = key.strip().lstrip("*#").rstrip("*").strip()
            clean_value = value.strip().lstrip("*").strip()
            if clean_key:
                result[clean_key] = clean_value
    return result
