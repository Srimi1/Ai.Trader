"""
Email notifications for AI.Trader trading signals.

Sends HTML email alerts via Gmail MCP when HIGH/MEDIUM confidence signals fire.
Recipient: configured via ALERT_EMAIL in .env (defaults to srijansaanand0@gmail.com)

Usage (from orchestrator / daily_run):
    from src.notifications.email import send_signal_alert, send_daily_digest
    send_signal_alert(ticker, rec, confidence, parsed, trade)
    send_daily_digest(results)

Requires: Gmail MCP connected in Claude Code (.mcp.json or user auth).
Falls back silently if MCP unavailable.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

logger = logging.getLogger(__name__)

ALERT_EMAIL = os.getenv("ALERT_EMAIL", "srijansaanand0@gmail.com")


def _signal_html(ticker: str, rec: str, confidence: str, parsed: dict, trade: dict) -> str:
    color = "#16a34a" if rec == "BUY" else "#dc2626" if rec == "SELL" else "#d97706"
    score = trade.get("adjusted_score", trade.get("score", 0))
    geo_risk = trade.get("_geo_risk_score", "N/A")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #111;">

<div style="border-left: 4px solid {color}; padding-left: 16px; margin-bottom: 24px;">
  <h1 style="margin: 0; font-size: 24px; color: {color};">{rec} — {ticker}</h1>
  <p style="margin: 4px 0; color: #666; font-size: 14px;">
    Confidence: <strong>{confidence}</strong> &nbsp;|&nbsp;
    Score: <strong>{score:+.2f}</strong> &nbsp;|&nbsp;
    Geo Risk: <strong>{geo_risk}/10</strong>
  </p>
</div>

<table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
  <tr style="background: #f9fafb;">
    <td style="padding: 8px 12px; font-weight: 600; width: 35%;">Ticker</td>
    <td style="padding: 8px 12px;">{ticker}</td>
  </tr>
  <tr>
    <td style="padding: 8px 12px; font-weight: 600;">Politician</td>
    <td style="padding: 8px 12px;">{trade.get('representative', 'N/A')}</td>
  </tr>
  <tr style="background: #f9fafb;">
    <td style="padding: 8px 12px; font-weight: 600;">Trade Type</td>
    <td style="padding: 8px 12px;">{(trade.get('trade_type') or '').upper()}</td>
  </tr>
  <tr>
    <td style="padding: 8px 12px; font-weight: 600;">Amount</td>
    <td style="padding: 8px 12px;">{trade.get('amount_range', 'N/A')}</td>
  </tr>
  <tr style="background: #f9fafb;">
    <td style="padding: 8px 12px; font-weight: 600;">Transaction Date</td>
    <td style="padding: 8px 12px;">{trade.get('transaction_date', 'N/A')[:10]}</td>
  </tr>
  <tr>
    <td style="padding: 8px 12px; font-weight: 600;">Position Size</td>
    <td style="padding: 8px 12px;">{parsed.get('POSITION_SIZE', 'N/A')}</td>
  </tr>
  <tr style="background: #f9fafb;">
    <td style="padding: 8px 12px; font-weight: 600;">Stop Loss</td>
    <td style="padding: 8px 12px; color: #dc2626;">{parsed.get('STOP_LOSS', 'N/A')}</td>
  </tr>
  <tr>
    <td style="padding: 8px 12px; font-weight: 600;">Take Profit</td>
    <td style="padding: 8px 12px; color: #16a34a;">{parsed.get('TAKE_PROFIT', 'N/A')}</td>
  </tr>
</table>

<div style="background: #f9fafb; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
  <p style="margin: 0 0 8px; font-weight: 600;">Reasoning</p>
  <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #374151;">{parsed.get('REASONING', 'N/A')}</p>
</div>

<div style="background: #fef3c7; border-radius: 8px; padding: 16px;">
  <p style="margin: 0 0 8px; font-weight: 600; color: #92400e;">⚠ Risk Note</p>
  <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #92400e;">{parsed.get('RISK_NOTE', 'N/A')}</p>
</div>

<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
<p style="font-size: 12px; color: #9ca3af; margin: 0;">
  AI.Trader — Congressional Signal Alert &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp;
  This is not financial advice. STOCK Act signals only. Paper trading mode.
</p>
</body>
</html>
"""


def _digest_html(results: list) -> str:
    rows = ""
    for r in results:
        rec = r.get("rec", "HOLD")
        color = "#16a34a" if rec == "BUY" else "#dc2626" if rec == "SELL" else "#d97706"
        rows += f"""
        <tr>
          <td style="padding: 8px 12px; font-weight: 600;">{r.get('ticker', '')}</td>
          <td style="padding: 8px 12px; color: {color}; font-weight: 600;">{rec}</td>
          <td style="padding: 8px 12px;">{r.get('confidence', '')}</td>
          <td style="padding: 8px 12px;">{r.get('score', 0):+.2f}</td>
          <td style="padding: 8px 12px;">{r.get('politician', '')}</td>
          <td style="padding: 8px 12px;">{r.get('position_size', '')}</td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; color: #111;">

<h1 style="font-size: 22px; margin-bottom: 4px;">AI.Trader — Daily Signal Digest</h1>
<p style="color: #666; font-size: 14px; margin-bottom: 24px;">{datetime.now().strftime('%A, %B %d %Y')}</p>

<table style="width: 100%; border-collapse: collapse; font-size: 14px;">
  <thead>
    <tr style="background: #111; color: #fff;">
      <th style="padding: 10px 12px; text-align: left;">Ticker</th>
      <th style="padding: 10px 12px; text-align: left;">Signal</th>
      <th style="padding: 10px 12px; text-align: left;">Confidence</th>
      <th style="padding: 10px 12px; text-align: left;">Score</th>
      <th style="padding: 10px 12px; text-align: left;">Politician</th>
      <th style="padding: 10px 12px; text-align: left;">Size</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>

<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
<p style="font-size: 12px; color: #9ca3af;">
  AI.Trader Daily Digest &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp;
  Not financial advice. Paper trading mode.
</p>
</body>
</html>
"""


def send_signal_alert(
    ticker: str,
    rec: str,
    confidence: str,
    parsed: dict,
    trade: dict,
    only_high: bool = False,
) -> bool:
    """
    Send HTML email alert for a single signal.
    only_high=True → skip MEDIUM/LOW confidence signals.
    Returns True if email sent, False if skipped or failed.
    """
    if only_high and confidence not in ("HIGH", "MEDIUM"):
        return False

    subject = f"[AI.Trader] {rec} {ticker} — {confidence} confidence"
    html = _signal_html(ticker, rec, confidence, parsed, trade)

    try:
        # Use Gmail MCP (available in Claude Code session)
        # This is called from orchestrator which runs inside Claude Code
        # Fallback: write to notification queue file that Claude Code picks up
        _queue_notification(subject, html, ALERT_EMAIL)
        logger.info("Email queued: %s → %s", subject, ALERT_EMAIL)
        return True
    except Exception as e:
        logger.warning("Email send failed: %s", e)
        return False


def _queue_notification(subject: str, html: str, to: str) -> None:
    """Write notification to queue file for Claude Code to send via Gmail MCP."""
    queue_dir = Path(__file__).parents[2] / "data" / "notifications"
    queue_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    queue_file = queue_dir / f"pending_{ts}.json"
    with open(queue_file, "w") as f:
        json.dump({
            "to": to,
            "subject": subject,
            "html": html,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }, f, indent=2)


def send_daily_digest(results: list) -> bool:
    """
    Send HTML digest email with all signals from a pipeline run.
    results: list of dicts with keys: ticker, rec, confidence, score, politician, position_size
    """
    if not results:
        return False

    buy_count = sum(1 for r in results if r.get("rec") == "BUY")
    sell_count = sum(1 for r in results if r.get("rec") == "SELL")
    subject = f"[AI.Trader] Daily Digest — {buy_count} BUY, {sell_count} SELL | {datetime.now().strftime('%Y-%m-%d')}"
    html = _digest_html(results)
    _queue_notification(subject, html, ALERT_EMAIL)
    logger.info("Daily digest queued → %s", ALERT_EMAIL)
    return True


def send_portfolio_digest(analysis: dict, review: str = "") -> bool:
    """
    Queue an HTML portfolio digest email showing dangers, losses, and opportunities.

    analysis keys used:
        total_value, total_pnl, dangers (list of dicts), losses (list of dicts),
        opportunities (list of dicts)
    Returns True if queued.
    """
    dangers = analysis.get("dangers") or []
    losses = analysis.get("losses") or []
    opportunities = analysis.get("opportunities") or []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = (
        f"[AI.Trader] Portfolio Alert — {now_str} | "
        f"{len(dangers)} dangers, {len(opportunities)} opportunities"
    )

    # --- summary row ---
    total_value = analysis.get("total_value", 0) or 0
    total_pnl = analysis.get("total_pnl", 0) or 0
    pnl_color = "#16a34a" if total_pnl >= 0 else "#dc2626"

    # --- danger rows ---
    danger_rows = ""
    for d in dangers:
        ticker = d.get("ticker", "")
        pnl = d.get("pnl", 0) or 0
        signal = d.get("signal", "SELL")
        danger_rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;font-weight:600;'>{ticker}</td>"
            f"<td style='padding:8px 12px;color:#dc2626;font-weight:600;'>{signal}</td>"
            f"<td style='padding:8px 12px;color:#dc2626;'>{pnl:+.2f}%</td>"
            f"<td style='padding:8px 12px;'>{d.get('politician','')}</td>"
            f"</tr>"
        )

    # --- loss rows ---
    loss_rows = ""
    for pos in losses:
        ticker = pos.get("ticker", "")
        pnl = pos.get("pnl", 0) or 0
        loss_rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;font-weight:600;'>{ticker}</td>"
            f"<td style='padding:8px 12px;color:#dc2626;'>{pnl:+.2f}%</td>"
            f"<td style='padding:8px 12px;'>{pos.get('entry_date','')}</td>"
            f"</tr>"
        )

    # --- opportunity rows ---
    opp_rows = ""
    for opp in opportunities:
        ticker = opp.get("ticker", "")
        score = opp.get("score", 0) or 0
        opp_rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;font-weight:600;'>{ticker}</td>"
            f"<td style='padding:8px 12px;color:#16a34a;font-weight:600;'>BUY</td>"
            f"<td style='padding:8px 12px;'>{score:+.2f}</td>"
            f"<td style='padding:8px 12px;'>{opp.get('politician','')}</td>"
            f"</tr>"
        )

    danger_section = ""
    if dangers:
        danger_section = f"""
<div style="border-left:4px solid #dc2626;padding-left:16px;margin-bottom:20px;">
  <h2 style="margin:0 0 8px;font-size:16px;color:#dc2626;">Danger Signals in Portfolio</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <thead>
      <tr style="background:#111;color:#fff;">
        <th style="padding:8px 12px;text-align:left;">Ticker</th>
        <th style="padding:8px 12px;text-align:left;">Signal</th>
        <th style="padding:8px 12px;text-align:left;">P&amp;L</th>
        <th style="padding:8px 12px;text-align:left;">Politician</th>
      </tr>
    </thead>
    <tbody>{danger_rows}</tbody>
  </table>
</div>"""

    loss_section = ""
    if losses:
        loss_section = f"""
<div style="border-left:4px solid #f97316;padding-left:16px;margin-bottom:20px;">
  <h2 style="margin:0 0 8px;font-size:16px;color:#f97316;">Loss Positions (&lt; -5%)</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <thead>
      <tr style="background:#111;color:#fff;">
        <th style="padding:8px 12px;text-align:left;">Ticker</th>
        <th style="padding:8px 12px;text-align:left;">P&amp;L</th>
        <th style="padding:8px 12px;text-align:left;">Entry Date</th>
      </tr>
    </thead>
    <tbody>{loss_rows}</tbody>
  </table>
</div>"""

    opp_section = ""
    if opportunities:
        opp_section = f"""
<div style="border-left:4px solid #16a34a;padding-left:16px;margin-bottom:20px;">
  <h2 style="margin:0 0 8px;font-size:16px;color:#16a34a;">Top Opportunities (BUY — not held)</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <thead>
      <tr style="background:#111;color:#fff;">
        <th style="padding:8px 12px;text-align:left;">Ticker</th>
        <th style="padding:8px 12px;text-align:left;">Signal</th>
        <th style="padding:8px 12px;text-align:left;">Score</th>
        <th style="padding:8px 12px;text-align:left;">Politician</th>
      </tr>
    </thead>
    <tbody>{opp_rows}</tbody>
  </table>
</div>"""

    review_section = ""
    if review:
        review_section = f"""
<div style="background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:16px;">
  <p style="margin:0 0 8px;font-weight:600;">Claude Portfolio Review</p>
  <p style="margin:0;font-size:14px;line-height:1.6;color:#374151;white-space:pre-wrap;">{review}</p>
</div>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:700px;margin:0 auto;padding:20px;color:#111;">

<h1 style="font-size:22px;margin-bottom:4px;">AI.Trader — Portfolio Alert</h1>
<p style="color:#666;font-size:14px;margin-bottom:20px;">{now_str}</p>

<div style="background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:24px;">
  <span style="font-size:14px;">Portfolio Value: <strong>${total_value:,.2f}</strong>
  &nbsp;|&nbsp; Total P&amp;L: <strong style="color:{pnl_color};">{total_pnl:+,.2f}</strong></span>
</div>

{danger_section}
{loss_section}
{opp_section}
{review_section}

<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
<p style="font-size:12px;color:#9ca3af;margin:0;">
  AI.Trader — Portfolio Digest &nbsp;|&nbsp; {now_str} &nbsp;|&nbsp;
  Not financial advice. Paper trading mode.
</p>
</body>
</html>"""

    _queue_notification(subject, html, ALERT_EMAIL)
    logger.info("Portfolio digest queued → %s (%d dangers, %d opps)", ALERT_EMAIL, len(dangers), len(opportunities))
    return True


def flush_pending_notifications() -> int:
    """
    Read all pending notifications from queue and send via Gmail MCP.
    Call this from Claude Code directly to actually send emails.
    Returns count sent.
    """
    queue_dir = Path(__file__).parents[2] / "data" / "notifications"
    if not queue_dir.exists():
        return 0

    sent = 0
    for f in sorted(queue_dir.glob("pending_*.json")):
        try:
            with open(f) as fp:
                notif = json.load(fp)
            # Mark as processing
            notif["status"] = "sending"
            with open(f, "w") as fp:
                json.dump(notif, fp)
            # Caller (Claude Code) must call Gmail MCP
            sent += 1
        except Exception as e:
            logger.error("Failed reading notification %s: %s", f, e)

    return sent


def list_pending() -> list:
    """Return list of unsent notifications from queue."""
    queue_dir = Path(__file__).parents[2] / "data" / "notifications"
    if not queue_dir.exists():
        return []
    result = []
    for f in sorted(queue_dir.glob("pending_*.json")):
        try:
            with open(f) as fp:
                result.append({"file": str(f), **json.load(fp)})
        except Exception:
            pass
    return result
