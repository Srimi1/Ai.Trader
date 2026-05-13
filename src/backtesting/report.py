"""HTML backtest report generation."""
from pathlib import Path
from typing import Optional

import pandas as pd

from src.backtesting.engine import BacktestMetrics


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Backtest Report — {date}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
.container {{ max-width: 900px; margin: 0 auto; background: white; padding: 32px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
h1 {{ color: #1a1a1a; margin-bottom: 8px; }}
h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 8px; margin-top: 32px; }}
.meta {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #eee; }}
th {{ background: #fafafa; font-weight: 600; color: #555; }}
tr:hover {{ background: #fafafa; }}
.metric-value {{ font-weight: 600; font-family: "SF Mono", Monaco, monospace; }}
.positive {{ color: #16a34a; }}
.negative {{ color: #dc2626; }}
.neutral {{ color: #525252; }}
.chart {{ margin-top: 24px; text-align: center; }}
.chart img {{ max-width: 100%; border-radius: 4px; }}
.footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #eee; color: #999; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="container">
<h1>📊 Political Alpha Backtest Report</h1>
<div class="meta">Generated on {date} · Engine: <strong>{engine}</strong></div>

<h2>Performance Summary</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{summary_rows}
</table>

<h2>Benchmark Comparison</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{benchmark_rows}
</table>

<h2>Trade Statistics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{trade_rows}
</table>

<div class="chart">
{chart_html}
</div>

<div class="footer">
AI.Trader · Phase 2 Backtesting Engine · Political Alpha Strategy
</div>
</div>
</body>
</html>
"""


def _fmt(value: float, suffix: str = "") -> str:
    if suffix == "%":
        color = "positive" if value > 0 else ("negative" if value < 0 else "neutral")
        sign = "+" if value > 0 else ""
        return f'<span class="metric-value {color}">{sign}{value:.2f}%</span>'
    return f'<span class="metric-value">{value:.3f}</span>'


def _row(label: str, value: str) -> str:
    return f"<tr><td>{label}</td><td>{value}</td></tr>\n"


def generate_report(
    metrics: BacktestMetrics,
    engine_name: str,
    chart_path: Optional[str] = None,
    output_path: str = "data/processed/reports/backtest_report.html",
) -> Path:
    """Generate HTML backtest report."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    summary = [
        ("Total Return", _fmt(metrics.total_return_pct, "%")),
        ("CAGR", _fmt(metrics.cagr_pct, "%")),
        ("Sharpe Ratio", _fmt(metrics.sharpe_ratio)),
        ("Sortino Ratio", _fmt(metrics.sortino_ratio)),
        ("Max Drawdown", _fmt(metrics.max_drawdown_pct, "%")),
        ("Calmar Ratio", _fmt(metrics.calmar_ratio)),
        ("Volatility (Annual)", _fmt(metrics.volatility_annual_pct, "%")),
    ]

    benchmark = [
        ("Strategy Return", _fmt(metrics.total_return_pct, "%")),
        ("SPY Benchmark", _fmt(metrics.benchmark_return_pct, "%")),
        ("Excess Return", _fmt(metrics.excess_return_pct, "%")),
        ("Alpha", _fmt(metrics.alpha)),
        ("Beta", _fmt(metrics.beta)),
    ]

    trades = [
        ("Number of Trades", f'<span class="metric-value">{metrics.num_trades}</span>'),
        ("Win Rate", _fmt(metrics.win_rate_pct, "%")),
        ("Profit Factor", _fmt(metrics.profit_factor)),
        ("Avg Trade Return", _fmt(metrics.avg_trade_return_pct, "%")),
    ]

    chart_html = (
        f'<img src="{chart_path}" alt="Equity Curve">'
        if chart_path and Path(chart_path).exists()
        else "<p><em>No chart generated.</em></p>"
    )

    html = HTML_TEMPLATE.format(
        date=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        engine=engine_name,
        summary_rows="".join(_row(l, v) for l, v in summary),
        benchmark_rows="".join(_row(l, v) for l, v in benchmark),
        trade_rows="".join(_row(l, v) for l, v in trades),
        chart_html=chart_html,
    )

    out.write_text(html, encoding="utf-8")
    return out
