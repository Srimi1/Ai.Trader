"""Unit tests for backtest metrics — pure math, no I/O."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))
from src.backtesting.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    win_rate,
    profit_factor,
    alpha_beta,
    annualized_volatility,
    cagr,
)


def _returns(values):
    return pd.Series(values, dtype=float)


def _equity(values):
    return pd.Series(values, dtype=float)


class TestSharpeRatio:
    def test_positive_returns_positive_sharpe(self):
        # varied positive returns (std > 0)
        r = _returns([0.01, 0.02, 0.005, 0.015, 0.008] * 50)
        assert sharpe_ratio(r) > 0

    def test_flat_returns_zero(self):
        r = _returns([0.0] * 252)
        assert sharpe_ratio(r) == 0.0

    def test_negative_returns_negative_sharpe(self):
        # varied negative returns (std > 0)
        r = _returns([-0.01, -0.02, -0.005, -0.015, -0.008] * 50)
        assert sharpe_ratio(r) < 0


class TestSortinoRatio:
    def test_only_gains_returns_zero(self):
        r = _returns([0.01] * 50)
        assert sortino_ratio(r) == 0.0

    def test_mixed_returns_positive(self):
        r = _returns([0.02, -0.005, 0.01, -0.002, 0.015] * 20)
        assert sortino_ratio(r) > 0


class TestMaxDrawdown:
    def test_flat_equity_zero_drawdown(self):
        eq = _equity([100.0] * 10)
        assert max_drawdown(eq) == 0.0

    def test_peak_then_drop(self):
        eq = _equity([100, 120, 90, 95])
        dd = max_drawdown(eq)
        assert dd < 0
        assert abs(dd - (-0.25)) < 0.001  # 90/120 - 1 = -0.25

    def test_rising_equity_zero_drawdown(self):
        eq = _equity([100, 110, 120, 130])
        assert max_drawdown(eq) == 0.0


class TestCalmarRatio:
    def test_positive_cagr_positive_mdd(self):
        assert calmar_ratio(0.15, -0.10) > 0

    def test_zero_mdd_returns_zero(self):
        assert calmar_ratio(0.15, 0.0) == 0.0


class TestWinRate:
    def test_all_wins(self):
        assert win_rate(_returns([0.01, 0.02, 0.005])) == 1.0

    def test_all_losses(self):
        assert win_rate(_returns([-0.01, -0.02])) == 0.0

    def test_half_wins(self):
        assert win_rate(_returns([0.01, -0.01])) == 0.5

    def test_empty_series(self):
        assert win_rate(_returns([])) == 0.0


class TestProfitFactor:
    def test_only_wins_returns_inf(self):
        import math
        assert math.isinf(profit_factor(_returns([0.01, 0.02])))

    def test_only_losses_returns_zero(self):
        assert profit_factor(_returns([-0.01, -0.02])) == 0.0

    def test_balanced(self):
        pf = profit_factor(_returns([0.02, -0.01]))
        assert pf == pytest.approx(2.0, rel=0.01)


class TestAlphaBeta:
    def test_identical_returns_beta_one(self):
        r = _returns([0.01, -0.005, 0.008, -0.002, 0.012] * 5)
        a, b = alpha_beta(r, r)
        assert b == pytest.approx(1.0, abs=0.01)

    def test_short_series_returns_zeros(self):
        r = _returns([0.01] * 5)
        a, b = alpha_beta(r, r)
        assert a == 0.0 and b == 0.0


class TestAnnualizedVolatility:
    def test_flat_returns_zero(self):
        assert annualized_volatility(_returns([0.0] * 100)) == 0.0

    def test_volatile_higher_than_stable(self):
        stable = _returns([0.001] * 100)
        volatile = _returns([0.02, -0.02] * 50)
        assert annualized_volatility(volatile) > annualized_volatility(stable)


class TestCagr:
    def test_doubling_over_1_year(self):
        assert cagr(100, 200, 1.0) == pytest.approx(1.0, rel=0.001)

    def test_zero_start_returns_zero(self):
        assert cagr(0, 200, 1.0) == 0.0

    def test_zero_years_returns_zero(self):
        assert cagr(100, 200, 0.0) == 0.0

    def test_negative_growth(self):
        assert cagr(100, 50, 1.0) < 0
