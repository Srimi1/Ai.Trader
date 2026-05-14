"""
SQLite trade journal for AI.Trader paper trading.

Tracks all signals and executed trades:
  - Logs every signal (even HOLD / skipped)
  - Records entry/exit price, P&L, hold duration
  - Provides summary stats: win rate, avg return, Sharpe

DB location: data/journal/trades.db
"""
import logging
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parents[2] / "data" / "journal" / "trades.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,
    signal              TEXT,                    -- BUY / SELL / NEUTRAL
    recommendation      TEXT,                    -- Claude: BUY / SELL / HOLD
    confidence          TEXT,                    -- HIGH / MEDIUM / LOW
    score               REAL,
    macro_score         REAL,
    geo_risk_score      REAL,
    position_size_pct   REAL,
    stop_loss           TEXT,
    take_profit         TEXT,
    reasoning           TEXT,
    risk_note           TEXT,
    representative      TEXT,
    amount_range        TEXT,
    transaction_date    TEXT,
    -- execution
    executed            INTEGER DEFAULT 0,       -- 1 = order placed
    order_id            TEXT,
    entry_date          TEXT,
    entry_price         REAL,
    qty                 REAL,
    -- outcome
    exit_date           TEXT,
    exit_price          REAL,
    pnl_pct             REAL,
    hold_days           INTEGER,
    status              TEXT DEFAULT 'logged',   -- logged / open / closed / skipped
    source              TEXT DEFAULT 'paper',    -- paper / live / dry_run
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_entry_date ON trades(entry_date);
"""


class Journal:
    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ── write ──────────────────────────────────────────────────────────────────

    def log_signal(
        self,
        trade: dict,
        parsed_rec: dict,
        order: Optional[dict] = None,
        source: str = "paper",
    ) -> int:
        """
        Log a signal + Claude recommendation. Returns row id.

        Args:
            trade: enriched trade dict from pipeline
            parsed_rec: output of parse_recommendation()
            order: Alpaca order dict if executed, else None
            source: 'paper' | 'live' | 'dry_run'
        """
        rec = parsed_rec.get("RECOMMENDATION", "HOLD")
        executed = 1 if order else 0

        # Parse position_size_pct from "3% of portfolio" → 0.03
        pos_str = parsed_rec.get("POSITION_SIZE", "")
        try:
            pos_pct = float(pos_str.replace("%", "").split()[0]) / 100
        except (ValueError, IndexError):
            pos_pct = None

        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trades (
                    ticker, signal, recommendation, confidence,
                    score, macro_score, geo_risk_score, position_size_pct,
                    stop_loss, take_profit, reasoning, risk_note,
                    representative, amount_range, transaction_date,
                    executed, order_id, entry_date, entry_price, qty,
                    status, source
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?
                )
                """,
                (
                    trade.get("ticker", ""),
                    trade.get("final_signal", trade.get("signal", "")),
                    rec,
                    parsed_rec.get("CONFIDENCE", ""),
                    trade.get("score"),
                    trade.get("macro_adjusted_score", trade.get("adjusted_score")),
                    trade.get("_geo_risk_score"),
                    pos_pct,
                    parsed_rec.get("STOP_LOSS", ""),
                    parsed_rec.get("TAKE_PROFIT", ""),
                    parsed_rec.get("REASONING", ""),
                    parsed_rec.get("RISK_NOTE", ""),
                    trade.get("representative", ""),
                    trade.get("amount_range", ""),
                    trade.get("transaction_date", ""),
                    executed,
                    order.get("order_id") if order else None,
                    order.get("entry_date", datetime.now().strftime("%Y-%m-%d")) if order else None,
                    order.get("entry_price") if order else None,
                    order.get("qty") if order else None,
                    "open" if executed else ("skipped" if rec == "HOLD" else "logged"),
                    source,
                ),
            )
            row_id = cursor.lastrowid
        logger.info("Journal: logged %s %s rec=%s id=%d", rec, trade.get("ticker"), rec, row_id)
        return row_id

    def close_trade(
        self,
        ticker: str,
        exit_price: float,
        exit_date: Optional[str] = None,
    ) -> Optional[int]:
        """
        Close the most recent open position for a ticker.
        Returns updated row id, or None if no open position found.
        """
        exit_date = exit_date or datetime.now().strftime("%Y-%m-%d")

        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, entry_price, entry_date FROM trades "
                "WHERE ticker=? AND status='open' ORDER BY id DESC LIMIT 1",
                (ticker.upper(),),
            ).fetchone()

            if not row:
                logger.warning("close_trade: no open position for %s", ticker)
                return None

            row_id = row["id"]
            entry_price = row["entry_price"]
            entry_date = row["entry_date"]

            pnl_pct = None
            hold_days = None
            if entry_price and entry_price > 0:
                pnl_pct = round((exit_price - entry_price) / entry_price * 100, 3)
            if entry_date:
                try:
                    entry = datetime.strptime(entry_date[:10], "%Y-%m-%d").date()
                    exit_d = datetime.strptime(exit_date[:10], "%Y-%m-%d").date()
                    hold_days = (exit_d - entry).days
                except ValueError:
                    pass

            conn.execute(
                """
                UPDATE trades SET
                    exit_date=?, exit_price=?, pnl_pct=?, hold_days=?, status='closed'
                WHERE id=?
                """,
                (exit_date, exit_price, pnl_pct, hold_days, row_id),
            )

        logger.info(
            "Journal: closed %s @ $%.2f | P&L: %+.2f%% | held %s days",
            ticker, exit_price, pnl_pct or 0, hold_days or "?",
        )
        return row_id

    def skip_trade(self, ticker: str, reason: str = "") -> None:
        """Mark a signal as skipped (e.g., market closed, position already held)."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE trades SET status='skipped', risk_note=? "
                "WHERE ticker=? AND status='logged' ORDER BY id DESC LIMIT 1",
                (reason, ticker.upper()),
            )

    # ── read ───────────────────────────────────────────────────────────────────

    def get_open_trades(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='open' ORDER BY entry_date DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_recent(self, limit: int = 20) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        """Return P&L summary across all closed trades."""
        with self._conn() as conn:
            closed = conn.execute(
                "SELECT pnl_pct, hold_days FROM trades WHERE status='closed' AND pnl_pct IS NOT NULL"
            ).fetchall()

            total = conn.execute("SELECT COUNT(*) FROM trades WHERE status NOT IN ('logged')").fetchone()[0]
            open_count = conn.execute("SELECT COUNT(*) FROM trades WHERE status='open'").fetchone()[0]

        if not closed:
            return {
                "total_signals": total,
                "open_positions": open_count,
                "closed_trades": 0,
                "win_rate_pct": None,
                "avg_pnl_pct": None,
                "total_pnl_pct": None,
                "avg_hold_days": None,
            }

        pnls = [r["pnl_pct"] for r in closed]
        wins = [p for p in pnls if p > 0]
        hold_days = [r["hold_days"] for r in closed if r["hold_days"]]

        return {
            "total_signals": total,
            "open_positions": open_count,
            "closed_trades": len(closed),
            "win_rate_pct": round(len(wins) / len(pnls) * 100, 1),
            "avg_pnl_pct": round(sum(pnls) / len(pnls), 2),
            "total_pnl_pct": round(sum(pnls), 2),
            "best_trade_pct": round(max(pnls), 2),
            "worst_trade_pct": round(min(pnls), 2),
            "avg_hold_days": round(sum(hold_days) / len(hold_days), 1) if hold_days else None,
        }


if __name__ == "__main__":
    import json
    j = Journal()
    print(json.dumps(j.summary(), indent=2))
    print(f"\nOpen trades: {len(j.get_open_trades())}")
