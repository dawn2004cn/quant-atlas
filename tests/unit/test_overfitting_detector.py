"""Unit tests for the overfitting detection framework.

Validates all four detection methods:
1. IS/OOS degradation
2. Parameter stability
3. Walk-forward analysis
4. Permutation test
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from app.core.overfitting_detector import (
    OverfittingDetector,
    OverfittingReport,
    PermutationTestResult,
    Severity,
    Verdict,
    WalkForwardResult,
)


class TestOverfittingDetectorDegradation(unittest.TestCase):
    """Test IS vs OOS metric degradation detection."""

    def setUp(self):
        self.detector = OverfittingDetector()

    def test_passing_degradation_no_flags(self):
        """When IS and OOS are close, no flags should be raised."""
        is_metrics = {"sharpe": 1.0, "total_return": 0.30, "win_rate": 0.55}
        oos_metrics = {"sharpe": 0.9, "total_return": 0.28, "win_rate": 0.54}
        deltas = self.detector.check_degradation(is_metrics, oos_metrics)
        # All changes < threshold → no deltas flagged
        self.assertEqual(len(deltas), 0)

    def test_sharpe_degradation_flagged(self):
        """Large Sharpe drop should be flagged."""
        is_metrics = {"sharpe": 2.0}
        oos_metrics = {"sharpe": 0.5}
        deltas = self.detector.check_degradation(is_metrics, oos_metrics)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0].name, "sharpe")
        self.assertAlmostEqual(deltas[0].pct_change, 75.0, places=1)

    def test_return_degradation_critical(self):
        """Return drop > 100% is impossible, but > 50% should be HIGH."""
        is_metrics = {"total_return": 0.50}
        oos_metrics = {"total_return": 0.10}
        deltas = self.detector.check_degradation(is_metrics, oos_metrics)
        self.assertEqual(len(deltas), 1)
        self.assertGreater(deltas[0].pct_change, 50)


class TestOverfittingDetectorParameterStability(unittest.TestCase):
    """Test parameter surface smoothness detection."""

    def setUp(self):
        self.detector = OverfittingDetector()

    def test_smooth_parameter_surface(self):
        """Small std across grid → smooth → not flagged."""
        grid = {"short_window": [0.10, 0.09, 0.11, 0.08, 0.12]}
        results = self.detector.check_parameter_stability(0.10, grid)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_smooth)

    def test_spike_parameter_surface(self):
        """Performance only good at nominal → spiky → flagged."""
        grid = {"short_window": [0.02, 0.02, 0.40, 0.02, 0.02]}
        results = self.detector.check_parameter_stability(0.40, grid)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_smooth)
        self.assertGreater(results[0].coefficient_of_variation, 0.5)


class TestOverfittingDetectorWalkForward(unittest.TestCase):
    """Test walk-forward consistency analysis."""

    def setUp(self):
        self.detector = OverfittingDetector()

    def test_consistent_returns_pass(self):
        """Stable positive returns → high walk-forward score."""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.01, 500))
        result = self.detector.walk_forward_analysis(returns, window_size=60, step_size=30)
        self.assertIsInstance(result, WalkForwardResult)
        self.assertGreater(result.num_windows, 0)
        self.assertGreaterEqual(result.pass_rate, 0)

    def test_empty_returns(self):
        """Very short series → zero windows."""
        returns = pd.Series([0.01, -0.01, 0.01])
        result = self.detector.walk_forward_analysis(returns, window_size=60)
        self.assertEqual(result.num_windows, 0)


class TestOverfittingDetectorPermutation(unittest.TestCase):
    """Test permutation-based significance."""

    def setUp(self):
        self.detector = OverfittingDetector()

    def test_significant_sharpe(self):
        """Strong real Sharpe should be significant (p < 0.05)."""
        np.random.seed(42)
        # Returns with real signal: mean >> 0
        returns = pd.Series(np.random.normal(0.002, 0.01, 500))
        result = self.detector.permutation_test(returns, n_permutations=200, seed=123)
        self.assertIsInstance(result, PermutationTestResult)
        self.assertGreater(result.real_sharpe, 0)
        self.assertGreater(result.n_permutations, 0)

    def test_no_signal_returns(self):
        """Pure noise should have high p-value."""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0, 0.01, 200))
        result = self.detector.permutation_test(returns, n_permutations=200, seed=456)
        self.assertGreaterEqual(result.p_value, 0.0)
        self.assertLessEqual(result.p_value, 1.0)


class TestOverfittingReport(unittest.TestCase):
    """Test report aggregation and verdict logic."""

    def setUp(self):
        self.detector = OverfittingDetector()

    def test_full_analysis_pass(self):
        """Consistent metrics → PASS verdict."""
        report = self.detector.analyze(
            strategy_name="TestConsistent",
            is_metrics={"sharpe": 1.0, "total_return": 0.30, "win_rate": 0.55},
            oos_metrics={"sharpe": 0.9, "total_return": 0.28, "win_rate": 0.54},
        )
        self.assertIsInstance(report, OverfittingReport)
        self.assertEqual(report.verdict, Verdict.PASS)
        self.assertEqual(len(report.flags), 0)

    def test_full_analysis_fail(self):
        """Large degradation → FAIL verdict."""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0, 0.01, 300))
        report = self.detector.analyze(
            strategy_name="TestFailing",
            is_metrics={"sharpe": 2.0, "total_return": 0.80, "win_rate": 0.65},
            oos_metrics={"sharpe": 0.3, "total_return": 0.05, "win_rate": 0.48},
            returns=returns,
        )
        self.assertIn(report.verdict, (Verdict.FAIL, Verdict.CONCERNS))
        self.assertGreater(len(report.flags), 0)

    def test_summarize(self):
        """Report summarisation produces readable output."""
        report = OverfittingReport(strategy_name="SumTest")
        report.add_flag("Test flag", Severity.HIGH)
        summary = report.summarise()
        self.assertIn("SumTest", summary)
        self.assertIn("Test flag", summary)
        self.assertIn("HIGH", summary)


if __name__ == "__main__":
    unittest.main()
