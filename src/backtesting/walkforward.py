"""Walk-forward validation — rolling train/test windows."""
from datetime import datetime, timedelta

from src.backtesting.engine import BacktestEngine


def _valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def rolling_walkforward(
    engine: BacktestEngine,
    signals: list[dict],
    train_days: int = 270,
    test_days: int = 90,
    step_days: int = 90,
    hold_days: int = 30,
    initial_cash: float = 100_000.0,
) -> list[dict]:
    """
    Run walk-forward analysis with rolling windows.

    Returns list of dicts, one per window:
        {
            "train_start", "train_end",
            "test_start", "test_end",
            "metrics": BacktestMetrics,
        }
    """
    dates = sorted({
        datetime.strptime(s["transaction_date"][:10], "%Y-%m-%d")
        for s in signals
        if s.get("transaction_date") and len(s["transaction_date"]) >= 10
        and _valid_date(s["transaction_date"])
    })
    if not dates:
        return []

    min_date = dates[0]
    max_date = dates[-1]

    results = []
    current = min_date + timedelta(days=train_days)

    while current + timedelta(days=test_days) <= max_date:
        train_start = min_date.strftime("%Y-%m-%d")
        train_end = current.strftime("%Y-%m-%d")
        test_start = current.strftime("%Y-%m-%d")
        test_end = (current + timedelta(days=test_days)).strftime("%Y-%m-%d")

        # Filter signals to OUT-OF-SAMPLE test window only (exclusive lower bound prevents leakage)
        test_signals = [
            s for s in signals
            if test_start < s.get("transaction_date", "") <= test_end
        ]

        engine.load_signals(test_signals, hold_days=hold_days)
        try:
            metrics = engine.run(
                start_date=train_start,
                end_date=test_end,
                initial_cash=initial_cash,
            )
        except Exception as e:
            print(f"      Window {test_start} → {test_end} failed: {e}")
            current += timedelta(days=step_days)
            continue

        results.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "metrics": metrics,
        })

        current += timedelta(days=step_days)

    return results


def summarize_walkforward(results: list[dict]) -> dict:
    """Aggregate statistics across all walk-forward windows."""
    if not results:
        return {}

    returns = [r["metrics"].total_return_pct for r in results]
    sharpes = [r["metrics"].sharpe_ratio for r in results]
    drawdowns = [r["metrics"].max_drawdown_pct for r in results]
    win_rates = [r["metrics"].win_rate_pct for r in results]

    return {
        "windows": len(results),
        "avg_return_pct": round(sum(returns) / len(returns), 2),
        "avg_sharpe": round(sum(sharpes) / len(sharpes), 3),
        "avg_drawdown_pct": round(sum(drawdowns) / len(drawdowns), 2),
        "avg_win_rate_pct": round(sum(win_rates) / len(win_rates), 2),
        "best_window_return_pct": round(max(returns), 2),
        "worst_window_return_pct": round(min(returns), 2),
        "consistency_score": round(
            sum(1 for r in returns if r > 0) / len(returns), 2
        ),  # % of positive windows
    }
