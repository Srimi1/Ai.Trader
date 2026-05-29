"""
Closed-loop scorecard — turns the trade journal into a learning loop.

Reads the signals logged by src.portfolio.journal (the `trades` table) and:
  - score_outcomes(): re-prices every BUY/SELL signal N days after it fired,
    compares to SPY over the same window, and stores a paper outcome — even for
    signals that were never executed. This measures the *signal's* quality.
  - attribution(): breaks win rate + excess-vs-SPY down by source so you can see
    which signal stream actually produced alpha.
  - track_record(): a compact, prompt-ready summary fed back into the decision
    agent so Claude reasons from its own measured history, not just the score.

Owns its own table (`signal_outcomes`) in the same SQLite DB as the journal.
"""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.portfolio.journal import _DB_PATH

logger = logging.getLogger(__name__)

_OUTCOMES_SCHEMA = """
-- One row per (signal, horizon). Evaluates the signal as a paper trade vs SPY,
-- independent of whether it was actually executed.
CREATE TABLE IF NOT EXISTS signal_outcomes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id            INTEGER NOT NULL,        -- FK -> trades.id
    horizon_days        INTEGER NOT NULL,        -- e.g. 7 / 30 / 90
    ref_date            TEXT,                    -- date the return is measured from
    signal_return_pct   REAL,                    -- directional return (sign-adjusted for SELL)
    spy_return_pct      REAL,                    -- SPY over the same window
    excess_return_pct   REAL,                    -- signal - SPY (directional)
    beat_benchmark      INTEGER,                 -- 1 = outperformed SPY
    outcome_label       TEXT,                    -- win / loss / flat
    scored_at           TEXT DEFAULT (datetime('now')),
    UNIQUE(trade_id, horizon_days)
);

CREATE INDEX IF NOT EXISTS idx_outcome_trade ON signal_outcomes(trade_id);
CREATE INDEX IF NOT EXISTS idx_outcome_horizon ON signal_outcomes(horizon_days);
"""


class Scorecard:
    """Outcome scoring + attribution over the journal's signal history."""

    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_OUTCOMES_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _ref_date(row: sqlite3.Row) -> Optional[str]:
        """Date a signal's paper return is measured from: entry if executed, else tx date."""
        return row["entry_date"] or row["transaction_date"]

    # ── scoring ──────────────────────────────────────────────────────────────────

    def score_outcomes(self, horizon_days: int = 30, price_fn=None, spy_fn=None) -> dict:
        """
        Re-price every BUY/SELL signal `horizon_days` after it fired and compare to SPY.

        Only signals whose reference date is at least `horizon_days` in the past (window
        elapsed) are scored, and each (signal, horizon) is scored at most once. Returns
        counts. price_fn / spy_fn are injectable for testing; default to ingestion.prices.
        """
        if price_fn is None or spy_fn is None:
            from src.ingestion.prices import get_return_since, get_spy_return
            price_fn = price_fn or get_return_since
            spy_fn = spy_fn or get_spy_return

        today = datetime.now().date()
        scored = wins = losses = skipped = 0

        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT t.* FROM trades t
                WHERE t.recommendation IN ('BUY', 'SELL')
                  AND NOT EXISTS (
                      SELECT 1 FROM signal_outcomes o
                      WHERE o.trade_id = t.id AND o.horizon_days = ?
                  )
                """,
                (horizon_days,),
            ).fetchall()

            for row in rows:
                ticker = row["ticker"]
                ref_date = self._ref_date(row)
                if not ticker or not ref_date:
                    continue
                try:
                    ref = datetime.strptime(ref_date[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
                # Window must have fully elapsed before we can score it.
                if (today - ref).days < horizon_days:
                    continue

                raw = price_fn(ticker, ref_date, horizon_days)
                spy = spy_fn(ref_date, horizon_days)
                if raw is None or spy is None:
                    skipped += 1
                    continue

                is_buy = row["recommendation"] == "BUY"
                # Sign-adjust so a correct SELL (price falls) is a positive signal return.
                signal_ret = raw if is_buy else -raw
                spy_dir = spy if is_buy else -spy
                excess = signal_ret - spy_dir
                label = "win" if signal_ret > 0 else ("loss" if signal_ret < 0 else "flat")

                conn.execute(
                    """
                    INSERT OR IGNORE INTO signal_outcomes (
                        trade_id, horizon_days, ref_date,
                        signal_return_pct, spy_return_pct, excess_return_pct,
                        beat_benchmark, outcome_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"], horizon_days, ref_date,
                        round(signal_ret * 100, 3),
                        round(spy * 100, 3),
                        round(excess * 100, 3),
                        1 if excess > 0 else 0,
                        label,
                    ),
                )
                scored += 1
                wins += label == "win"
                losses += label == "loss"

        logger.info(
            "Scorecard: scored %d outcomes @ %dd horizon (%d win / %d loss, %d skipped)",
            scored, horizon_days, wins, losses, skipped,
        )
        return {
            "horizon_days": horizon_days,
            "scored": scored,
            "wins": wins,
            "losses": losses,
            "skipped_no_price": skipped,
        }

    # ── analysis ─────────────────────────────────────────────────────────────────

    def attribution(self, horizon_days: int = 30) -> dict:
        """
        Break win rate + avg excess-vs-SPY down by signal source.

        Returns overall stats plus per-dimension buckets (sentiment source, confidence,
        recommendation) so you can see which stream actually produced alpha.
        """
        def _bucket(group_col: str) -> list:
            with self._conn() as conn:
                rows = conn.execute(
                    f"""
                    SELECT COALESCE(t.{group_col}, 'unknown') AS bucket,
                           COUNT(*)                            AS n,
                           SUM(o.outcome_label = 'win')        AS wins,
                           AVG(o.signal_return_pct)            AS avg_return_pct,
                           AVG(o.excess_return_pct)            AS avg_excess_pct,
                           SUM(o.beat_benchmark)               AS beat_spy
                    FROM signal_outcomes o
                    JOIN trades t ON t.id = o.trade_id
                    WHERE o.horizon_days = ?
                    GROUP BY bucket
                    ORDER BY avg_excess_pct DESC
                    """,
                    (horizon_days,),
                ).fetchall()
            out = []
            for r in rows:
                n = r["n"] or 0
                out.append({
                    "bucket": r["bucket"],
                    "n": n,
                    "win_rate_pct": round((r["wins"] or 0) / n * 100, 1) if n else None,
                    "avg_return_pct": round(r["avg_return_pct"], 2) if r["avg_return_pct"] is not None else None,
                    "avg_excess_pct": round(r["avg_excess_pct"], 2) if r["avg_excess_pct"] is not None else None,
                    "beat_spy_pct": round((r["beat_spy"] or 0) / n * 100, 1) if n else None,
                })
            return out

        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM signal_outcomes WHERE horizon_days=?", (horizon_days,)
            ).fetchone()[0]

        return {
            "horizon_days": horizon_days,
            "scored_signals": total,
            "by_source": _bucket("sentiment_source"),
            "by_confidence": _bucket("confidence"),
            "by_recommendation": _bucket("recommendation"),
        }

    def track_record(self, ticker: Optional[str] = None, horizon_days: int = 30) -> str:
        """
        Compact, prompt-ready summary of measured performance, fed back into the
        decision agent so Claude reasons from its own history. Returns '' when there
        is no scored history yet (caller can skip injecting the block).
        """
        with self._conn() as conn:
            overall = conn.execute(
                """
                SELECT COUNT(*) AS n, SUM(outcome_label='win') AS wins,
                       AVG(signal_return_pct) AS ret, AVG(excess_return_pct) AS excess
                FROM signal_outcomes WHERE horizon_days=?
                """,
                (horizon_days,),
            ).fetchone()

            if not overall or not overall["n"]:
                return ""

            n = overall["n"]
            win_rate = (overall["wins"] or 0) / n * 100
            lines = [
                f"Track Record (your past {horizon_days}-day signal outcomes, n={n}):",
                f"  Overall: {win_rate:.0f}% win rate | "
                f"avg signal return {overall['ret']:+.2f}% | "
                f"avg vs SPY {overall['excess']:+.2f}%",
            ]

            src_rows = conn.execute(
                """
                SELECT COALESCE(t.sentiment_source,'unknown') AS src, COUNT(*) AS n,
                       AVG(o.excess_return_pct) AS excess
                FROM signal_outcomes o JOIN trades t ON t.id=o.trade_id
                WHERE o.horizon_days=? GROUP BY src HAVING n >= 2
                ORDER BY excess DESC
                """,
                (horizon_days,),
            ).fetchall()
            for r in src_rows:
                lines.append(f"  Source '{r['src']}': avg vs SPY {r['excess']:+.2f}% (n={r['n']})")

            if ticker:
                tr = conn.execute(
                    """
                    SELECT COUNT(*) AS n, AVG(o.excess_return_pct) AS excess
                    FROM signal_outcomes o JOIN trades t ON t.id=o.trade_id
                    WHERE o.horizon_days=? AND t.ticker=?
                    """,
                    (horizon_days, ticker.upper()),
                ).fetchone()
                if tr and tr["n"]:
                    lines.append(
                        f"  This ticker ({ticker.upper()}): "
                        f"avg vs SPY {tr['excess']:+.2f}% over {tr['n']} prior signal(s)"
                    )

        return "\n".join(lines)


if __name__ == "__main__":
    import json
    sc = Scorecard()
    print(json.dumps(sc.attribution(30), indent=2))
