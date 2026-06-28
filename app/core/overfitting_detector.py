"""Overfitting detection framework for quantitative strategies.

Provides statistical tests to flag strategies that perform well on
in-sample data but degrade out-of-sample — a known audit finding
(H11: 策略回测胜率虚高 5-15%).

Detection methods:
  1. **In-sample / Out-of-sample degradation** — compares IS vs OOS Sharpe,
     return, and win rate. Flags when OOS drops > X% below IS.
  2. **Parameter stability** — runs a grid around nominal parameters and
     checks if performance is a smooth function (not a spike).
  3. **Walk-forward analysis** — splits data into rolling windows,
     computes forward-compounded return consistency.
  4. **Permutation test** — shuffles labels to establish a null distribution;
     flags if real alpha is not significantly above zero.

All methods return a structured ``OverfittingReport`` with verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd

# ─── Enums ─────────────────────────────────────────────────────────────


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(Enum):
    PASS = "pass"
    CONCERNS = "concerns"
    FAIL = "fail"


# ─── Data classes ─────────────────────────────────────────────────────


@dataclass
class MetricDelta:
    """Difference between IS and OOS for a single metric."""

    name: str
    is_value: float
    oos_value: float
    pct_change: float  # negative = degradation
    severity: Severity = Severity.LOW

    @property
    def flag(self) -> bool:
        return self.severity in (Severity.HIGH, Severity.CRITICAL)


@dataclass
class ParameterStabilityResult:
    """Results from parameter perturbation analysis."""

    parameter: str
    nominal_performance: float
    std_across_grid: float
    coefficient_of_variation: float  # std / mean
    is_smooth: bool  # True if performance doesn't spike at nominal
    severity: Severity = Severity.LOW


@dataclass
class WalkForwardResult:
    """Results from walk-forward analysis."""

    num_windows: int
    passing_windows: int  # OOS Sharpe > 0
    pass_rate: float
    mean_oos_sharpe: float
    std_oos_sharpe: float
    consistency_score: float  # 0-1, how consistent the strategy is
    severity: Severity = Severity.LOW


@dataclass
class PermutationTestResult:
    """Results from permutation (shuffle) test."""

    real_sharpe: float
    mean_null_sharpe: float
    std_null_sharpe: float
    p_value: float  # proportion of shuffled sharpes >= real sharpe
    is_significant: bool
    n_permutations: int
    severity: Severity = Severity.LOW


@dataclass
class OverfittingReport:
    """Consolidated overfitting assessment for a strategy."""

    strategy_name: str
    verdict: Verdict = Verdict.PASS
    severity: Severity = Severity.LOW

    # Individual test results
    degradation: list[MetricDelta] = field(default_factory=list)
    parameter_stability: list[ParameterStabilityResult] = field(default_factory=list)
    walk_forward: WalkForwardResult | None = None
    permutation_test: PermutationTestResult | None = None

    # Summary flags
    flags: list[str] = field(default_factory=list)

    def add_flag(self, msg: str, severity: Severity) -> None:
        self.flags.append(f"[{severity.value.upper()}] {msg}")
        if severity.value in ("critical", "high") or self.severity.value in ("medium", "low"):
            self.severity = severity
        if severity == Severity.CRITICAL:
            self.verdict = Verdict.FAIL
        elif severity == Severity.HIGH and self.verdict != Verdict.FAIL:
            self.verdict = Verdict.CONCERNS
        elif severity == Severity.MEDIUM and self.verdict == Verdict.PASS:
            self.verdict = Verdict.CONCERNS

    def summarise(self) -> str:
        lines = [f"Overfitting Report: {self.strategy_name} — {self.verdict.value.upper()}"]
        if self.flags:
            for f in self.flags:
                lines.append(f"  - {f}")
        else:
            lines.append("  No flags.")
        return "\n".join(lines)


# ─── Thresholds ────────────────────────────────────────────────────────

_DEFAULT_THRESHOLDS = {
    "sharpe_degradation_pct": 30.0,    # OOS Sharpe < 70% of IS → flag
    "return_degradation_pct": 50.0,    # OOS return < 50% of IS → flag
    "winrate_degradation_pct": 10.0,   # OOS win rate drop > 10pp → flag
    "param_cv_threshold": 0.5,         # CV > 0.5 → spiky parameter surface
    "walkforward_pass_rate": 0.6,      # < 60% windows profitable → flag
    "walkforward_mean_sharpe": 0.0,    # mean OOS Sharpe <= 0 → flag
    "permutation_pvalue": 0.05,        # p > 0.05 → not significant
    "min_trades_for_test": 20,         # fewer trades → skip permutation
}


# ─── Core detector ───────────────────────────────────────────────────


class OverfittingDetector:
    """Statistical overfitting detector for quant strategies.

    Usage:
        detector = OverfittingDetector()
        report = detector.analyze(
            strategy_name="DualMA",
            is_returns=is_returns_series,
            oos_returns=oos_returns_series,
            is_metrics={"sharpe": 1.2, "total_return": 0.35, "win_rate": 0.58},
            oos_metrics={"sharpe": 0.6, "total_return": 0.12, "win_rate": 0.45},
            trades=trade_records,
        )
    """

    def __init__(self, thresholds: dict[str, float] | None = None):
        self.thresh = {**_DEFAULT_THRESHOLDS, **(thresholds or {})}

    # ── 1. IS vs OOS degradation ──────────────────────────────────────

    def check_degradation(
        self,
        is_metrics: dict[str, float],
        oos_metrics: dict[str, float],
    ) -> list[MetricDelta]:
        """Compare in-sample vs out-of-sample metrics."""
        deltas: list[MetricDelta] = []
        mapping = {
            "sharpe": ("sharpe_degradation_pct", Severity.MEDIUM),
            "total_return": ("return_degradation_pct", Severity.HIGH),
            "win_rate": ("winrate_degradation_pct", Severity.MEDIUM),
            "max_drawdown": ("return_degradation_pct", Severity.CRITICAL),
            "calmar_ratio": ("sharpe_degradation_pct", Severity.MEDIUM),
            "sortino_ratio": ("sharpe_degradation_pct", Severity.MEDIUM),
        }
        for name, (threshold_key, sev_base) in mapping.items():
            is_val = is_metrics.get(name)
            oos_val = oos_metrics.get(name)
            if is_val is None or oos_val is None:
                continue
            if name == "max_drawdown":
                # More negative is worse; degradation = OOS is more negative
                pct = ((is_val - oos_val) / abs(is_val) * 100) if is_val else 0
            else:
                pct = ((is_val - oos_val) / abs(is_val) * 100) if is_val else 0
            threshold_pct = self.thresh[threshold_key]
            if pct > threshold_pct:
                severity = (
                    Severity.CRITICAL if pct > threshold_pct * 2
                    else Severity.HIGH if pct > threshold_pct * 1.5
                    else sev_base
                )
                deltas.append(MetricDelta(
                    name=name,
                    is_value=is_val,
                    oos_value=oos_val,
                    pct_change=pct,
                    severity=severity,
                ))
        return deltas

    # ── 2. Parameter stability ────────────────────────────────────────

    def check_parameter_stability(
        self,
        base_performance: float,
        grid_results: dict[str, list[float]],
    ) -> list[ParameterStabilityResult]:
        """Check if performance spikes only at nominal parameters.

        Args:
            base_performance: Performance at nominal parameter values.
            grid_results: Mapping from parameter name → list of performance
                values across the grid (including nominal).

        Returns:
            One result per parameter.
        """
        results: list[ParameterStabilityResult] = []
        cv_threshold = self.thresh["param_cv_threshold"]
        for param, perf_list in grid_results.items():
            arr = np.array(perf_list, dtype=float)
            mean = arr.mean()
            std = arr.std()
            cv = std / abs(mean) if mean else 0.0
            is_smooth = cv <= cv_threshold
            severity = (
                Severity.CRITICAL if cv > cv_threshold * 3
                else Severity.HIGH if cv > cv_threshold * 2
                else Severity.MEDIUM if cv > cv_threshold
                else Severity.LOW
            )
            results.append(ParameterStabilityResult(
                parameter=param,
                nominal_performance=base_performance,
                std_across_grid=std,
                coefficient_of_variation=cv,
                is_smooth=is_smooth,
                severity=severity,
            ))
        return results

    # ── 3. Walk-forward analysis ─────────────────────────────────────

    def walk_forward_analysis(
        self,
        returns: pd.Series,
        window_size: int = 60,
        step_size: int = 30,
    ) -> WalkForwardResult:
        """Rolling window analysis: IS for training, OOS for evaluation.

        Args:
            returns: Daily returns series.
            window_size: Total window size in bars.
            step_size: Step between windows.

        Returns:
            WalkForwardResult with consistency metrics.
        """
        n = len(returns)
        if n < window_size:
            return WalkForwardResult(
                num_windows=0, passing_windows=0, pass_rate=0.0,
                mean_oos_sharpe=0.0, std_oos_sharpe=0.0,
                consistency_score=0.0, severity=Severity.LOW,
            )

        oos_sharpes: list[float] = []
        for start in range(0, n - window_size, step_size):
            end = start + window_size
            window = returns.iloc[start:end]
            oos = window.iloc[-(window_size // 3):]  # last third is OOS
            if oos.std() < 1e-10:
                continue
            sharpe = oos.mean() / oos.std() * np.sqrt(252)
            oos_sharpes.append(sharpe)

        if not oos_sharpes:
            return WalkForwardResult(
                num_windows=0, passing_windows=0, pass_rate=0.0,
                mean_oos_sharpe=0.0, std_oos_sharpe=0.0,
                consistency_score=0.0, severity=Severity.LOW,
            )

        arr = np.array(oos_sharpes)
        passing = int(np.sum(arr > self.thresh["walkforward_mean_sharpe"]))
        pass_rate = passing / len(arr)
        consistency = min(pass_rate, abs(arr.mean()) / (arr.std() + 1e-10))

        severity = Severity.LOW
        if pass_rate < self.thresh["walkforward_pass_rate"]:
            severity = Severity.HIGH
        if arr.mean() <= 0:
            severity = Severity.CRITICAL

        return WalkForwardResult(
            num_windows=len(arr),
            passing_windows=passing,
            pass_rate=pass_rate,
            mean_oos_sharpe=float(arr.mean()),
            std_oos_sharpe=float(arr.std()),
            consistency_score=float(consistency),
            severity=severity,
        )

    # ── 4. Permutation test ──────────────────────────────────────────

    def permutation_test(
        self,
        returns: pd.Series,
        n_permutations: int = 1000,
        seed: int = 42,
    ) -> PermutationTestResult:
        """Shuffle returns to build a null distribution of Sharpe ratios.

        If the real Sharpe is not significantly above the null, the
        strategy's alpha is likely overfit.
        """
        if len(returns) < self.thresh["min_trades_for_test"]:
            return PermutationTestResult(
                real_sharpe=float(returns.std()),
                mean_null_sharpe=0.0, std_null_sharpe=0.0,
                p_value=1.0, is_significant=False,
                n_permutations=n_permutations,
                severity=Severity.LOW,
            )

        rng = np.random.RandomState(seed)
        real_sharpe = returns.mean() / returns.std() * np.sqrt(252)

        null_sharpes = np.empty(n_permutations)
        for i in range(n_permutations):
            shuffled = returns.sample(frac=1, replace=False, random_state=rng.randint(0, 2**31))
            if shuffled.std() < 1e-10:
                null_sharpes[i] = 0.0
            else:
                null_sharpes[i] = shuffled.mean() / shuffled.std() * np.sqrt(252)

        p_value = float(np.mean(null_sharpes >= real_sharpe))
        is_significant = p_value < self.thresh["permutation_pvalue"]

        severity = Severity.LOW
        if p_value > 0.2:
            severity = Severity.CRITICAL
        elif p_value > 0.1:
            severity = Severity.HIGH
        elif p_value > 0.05:
            severity = Severity.MEDIUM

        return PermutationTestResult(
            real_sharpe=real_sharpe,
            mean_null_sharpe=float(null_sharpes.mean()),
            std_null_sharpe=float(null_sharpes.std()),
            p_value=p_value,
            is_significant=is_significant,
            n_permutations=n_permutations,
            severity=severity,
        )

    # ── Orchestrator ─────────────────────────────────────────────────

    def analyze(
        self,
        strategy_name: str,
        is_metrics: dict[str, float] | None = None,
        oos_metrics: dict[str, float] | None = None,
        returns: pd.Series | None = None,
        grid_results: dict[str, list[float]] | None = None,
        base_performance: float = 0.0,
        n_permutations: int = 1000,
    ) -> OverfittingReport:
        """Run all available overfitting checks and return a report.

        Args:
            strategy_name: Human-readable strategy name.
            is_metrics: In-sample metrics dict (sharpe, total_return, win_rate, ...).
            oos_metrics: Out-of-sample metrics dict (same keys).
            returns: Full returns series (used for walk-forward + permutation).
            grid_results: Parameter grid performance for stability check.
            base_performance: Nominal parameter performance.
            n_permutations: Number of permutation test iterations.

        Returns:
            OverfittingReport with verdict.
        """
        report = OverfittingReport(strategy_name=strategy_name)

        # 1. Degradation check
        if is_metrics and oos_metrics:
            deltas = self.check_degradation(is_metrics, oos_metrics)
            report.degradation = deltas
            for d in deltas:
                if d.flag:
                    report.add_flag(
                        f"{d.name}: IS={d.is_value:.3f} → OOS={d.oos_value:.3f} "
                        f"({d.pct_change:+.1f}%)",
                        d.severity,
                    )

        # 2. Parameter stability
        if grid_results is not None:
            stability = self.check_parameter_stability(base_performance, grid_results)
            report.parameter_stability = stability
            for s in stability:
                if not s.is_smooth:
                    report.add_flag(
                        f"Parameter '{s.parameter}' is spiky "
                        f"(CV={s.coefficient_of_variation:.2f})",
                        s.severity,
                    )

        # 3. Walk-forward (needs returns series)
        if returns is not None:
            wf = self.walk_forward_analysis(returns)
            report.walk_forward = wf
            if wf.severity in (Severity.HIGH, Severity.CRITICAL):
                report.add_flag(
                    f"Walk-forward: {wf.passing_windows}/{wf.num_windows} windows pass "
                    f"(mean OOS Sharpe={wf.mean_oos_sharpe:.3f})",
                    wf.severity,
                )

        # 4. Permutation test
        if returns is not None:
            perm = self.permutation_test(returns, n_permutations)
            report.permutation_test = perm
            if not perm.is_significant:
                report.add_flag(
                    f"Permutation test: p={perm.p_value:.3f} "
                    f"(real Sharpe={perm.real_sharpe:.3f}, "
                    f"null mean={perm.mean_null_sharpe:.3f})",
                    perm.severity,
                )

        # Final verdict
        if report.verdict == Verdict.PASS and not report.flags:
            report.verdict = Verdict.PASS
        elif report.severity in (Severity.HIGH, Severity.CRITICAL):
            report.verdict = Verdict.FAIL

        return report
