"""
Macro context enrichment using WorldMonitor data.

Applies VIX-based risk multiplier and sector momentum to scored trades.
Run after signals.py scoring, before decision_agent.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.ingestion.worldmonitor import (
    get_macro_snapshot,
    get_vix_risk_multiplier,
    get_sector_for_ticker,
    get_sector_etf_for_ticker,
)

_SECTOR_MOMENTUM_THRESHOLDS = {
    "strong_bull": (3.0, 1.15),   # sector +3%+ → 15% boost
    "bull":        (1.0, 1.05),   # sector +1-3% → 5% boost
    "neutral":     (0.0, 1.00),   # sector ±1% → no change
    "bear":       (-3.0, 0.92),   # sector -1 to -3% → 8% penalize
    "strong_bear": (None, 0.80),  # sector < -3% → 20% penalize
}


def _sector_momentum_multiplier(return_pct) -> float:
    if return_pct is None:
        return 1.0
    if return_pct >= 3.0:
        return 1.15
    if return_pct >= 1.0:
        return 1.05
    if return_pct >= -1.0:
        return 1.00
    if return_pct >= -3.0:
        return 0.92
    return 0.80


def apply_macro_context(scored_trades: list, verbose: bool = True) -> tuple:
    """
    Enrich scored trades with macro context from WorldMonitor.

    Returns (enriched_trades, macro_snapshot).
    Each trade gains:
      - 'macro_vix_multiplier': VIX-based risk factor
      - 'macro_sector_multiplier': sector momentum factor
      - 'macro_adjusted_score': score after both multipliers
      - 'macro_context': summary dict
    """
    snapshot = get_macro_snapshot(lookback_days=20)

    vix_val = snapshot.get("vix", {}).get("current")
    vix_mult = get_vix_risk_multiplier(vix_val)

    if verbose:
        vix_str = f"{vix_val:.1f}" if vix_val else "N/A"
        print(f"      VIX={vix_str} → risk multiplier={vix_mult:.2f}")

    enriched = []
    for trade in scored_trades:
        ticker = trade.get("ticker", "")
        sector = get_sector_for_ticker(ticker)
        sector_etf = get_sector_etf_for_ticker(ticker)
        sector_return = None
        if sector and sector in snapshot.get("sectors", {}):
            sector_return = snapshot["sectors"][sector].get("return_pct")
        sector_mult = _sector_momentum_multiplier(sector_return)

        base_score = trade.get("adjusted_score", trade.get("score", 0))
        macro_score = round(base_score * vix_mult * sector_mult, 3)

        enriched.append({
            **trade,
            "macro_vix_multiplier": vix_mult,
            "macro_sector_multiplier": sector_mult,
            "macro_adjusted_score": macro_score,
            "macro_context": {
                "vix": vix_val,
                "sector": sector,
                "sector_etf": sector_etf,
                "sector_20d_return": sector_return,
            },
        })

    # re-sort by macro_adjusted_score magnitude
    enriched.sort(key=lambda x: abs(x["macro_adjusted_score"]), reverse=True)
    return enriched, snapshot


if __name__ == "__main__":
    from src.ingestion.congress import get_recent_trades
    from src.analysis.signals import score_all
    from src.analysis.sentiment import apply_sentiment

    trades = get_recent_trades(days=90)
    scored = score_all(trades)
    enriched_sentiment = apply_sentiment(scored[:10])
    enriched_macro, snap = apply_macro_context(enriched_sentiment)

    print(f"\nTop signals after macro context ({len(enriched_macro)} trades):\n")
    for t in enriched_macro[:5]:
        print(
            f"[{t['transaction_date']}] {t['ticker']:6s} "
            f"score={t.get('adjusted_score',0):+.3f} "
            f"→ macro={t['macro_adjusted_score']:+.3f} "
            f"(VIX×{t['macro_vix_multiplier']:.2f} "
            f"sector×{t['macro_sector_multiplier']:.2f}) "
            f"sector={t['macro_context']['sector'] or 'unknown'}"
        )
