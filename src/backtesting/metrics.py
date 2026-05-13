"""Standardized backtest metrics calculation."""
import numpy as np
import pandas as pd


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Annualized Sharpe ratio."""
    excess = returns - risk_free / 252
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(252))


def sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    excess = returns - risk_free / 252
    downside = excess[excess < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    return float(excess.mean() / downside.std() * np.sqrt(252))


def max_drawdown(equity: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a negative decimal."""
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    return float(drawdown.min())


def calmar_ratio(cagr: float, mdd: float) -> float:
    """Calmar = CAGR / |max drawdown|."""
    return abs(cagr / mdd) if mdd != 0 else 0.0


def win_rate(trade_returns: pd.Series) -> float:
    """Percentage of winning trades."""
    if len(trade_returns) == 0:
        return 0.0
    return float((trade_returns > 0).sum() / len(trade_returns))


def profit_factor(trade_returns: pd.Series) -> float:
    """Gross profit / gross loss."""
    gross_won = trade_returns[trade_returns > 0].sum()
    gross_lost = abs(trade_returns[trade_returns < 0].sum())
    if gross_lost != 0:
        return float(gross_won / gross_lost)
    return float("inf") if gross_won > 0 else 0.0


def alpha_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> tuple[float, float]:
    """Calculate alpha (annualized) and beta."""
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 10:
        return 0.0, 0.0
    pr = aligned.iloc[:, 0]
    br = aligned.iloc[:, 1]
    cov = np.cov(pr, br)[0, 1]
    var = np.var(br, ddof=1)  # match ddof with np.cov
    beta = float(cov / var) if var != 0 else 0.0
    alpha = float(pr.mean() - beta * br.mean()) * 252
    return alpha, beta


def annualized_volatility(returns: pd.Series) -> float:
    """Annualized standard deviation of returns."""
    return float(returns.std() * np.sqrt(252))


def cagr(start_value: float, end_value: float, years: float) -> float:
    """Compound Annual Growth Rate."""
    if start_value <= 0 or years <= 0:
        return 0.0
    return float((end_value / start_value) ** (1 / years) - 1)
