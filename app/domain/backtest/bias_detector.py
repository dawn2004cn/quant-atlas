"""Look-ahead bias detection for backtest data pipelines.

Detects common forward-looking bias patterns:
1. Future data leakage (timestamps in wrong order)
2. Dividend/split adjustments applied inconsistently
3. Signal using data not available at prediction time
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BiasReport:
    """Result of a look-ahead bias scan."""
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class LookAheadBiasDetector:
    """Detect look-ahead bias in backtest data and trade signals."""

    def check_data_timestamps(self, df: pd.DataFrame, date_col: str = "date") -> BiasReport:
        """Verify no future timestamps exist in the dataset."""
        warnings = []
        if df.empty:
            return BiasReport(passed=True, warnings=["Empty dataset"])
        if date_col not in df.columns:
            return BiasReport(passed=True, warnings=["No date column to check"])
        now = datetime.now()
        future = df[df[date_col] > now]
        if len(future) > 0:
            warnings.append(f"{len(future)} rows have future timestamps (potential look-ahead)")
        return BiasReport(passed=len(warnings) == 0, warnings=warnings)

    def check_sorted_ascending(self, df: pd.DataFrame, date_col: str = "date") -> BiasReport:
        """Verify data is sorted ascending (oldest first)."""
        warnings = []
        if df.empty or date_col not in df.columns:
            return BiasReport(passed=True)
        df[date_col].sort_values()
        if not df[date_col].is_monotonic_increasing:
            # Check if it's sorted descending instead
            if df[date_col].is_monotonic_decreasing:
                warnings.append("Data is sorted descending (newest first) — may cause forward-looking bias if slice ordering is assumed")
            else:
                warnings.append("Data is not monotonically sorted — check for temporal consistency")
        return BiasReport(passed=len(warnings) == 0, warnings=warnings)

    def check_signal_vs_data_alignment(self, signal_date: str, data_end_date: str) -> BiasReport:
        """Verify a trade signal date does not exceed available data."""
        errors = []
        if signal_date and data_end_date and signal_date > data_end_date:
            errors.append(f"Signal date {signal_date} is after available data {data_end_date} — look-ahead bias detected")
        return BiasReport(passed=len(errors) == 0, errors=errors)

    def validate_split_adjustment(self, df: pd.DataFrame, price_cols: list[str] | None = None) -> BiasReport:
        """Check for split/dividend adjustment consistency."""
        warnings = []
        cols = price_cols or ["open", "high", "low", "close"]
        for col in cols:
            if col not in df.columns:
                continue
            # Detect extreme single-day moves (>90%) which may indicate unadjusted splits
            pct_changes = df[col].pct_change().abs()
            extreme = pct_changes > 0.9
            extreme_count = extreme.sum()
            if extreme_count > 0:
                warnings.append(f"Column '{col}' has {extreme_count} days with >90% move (possible unadjusted split)")
        return BiasReport(passed=len(warnings) == 0, warnings=warnings)


class BiasGateError(ValueError):
    """Raised when look-ahead bias gate blocks tournament / paper enrollment."""

    def __init__(self, report: BiasReport) -> None:
        self.report = report
        detail = "; ".join(report.errors or report.warnings) or "bias_gate_failed"
        super().__init__(f"bias_gate_blocked:{detail}")


def passes_bias_gate(report: BiasReport, *, treat_warnings_as_fail: bool = False) -> bool:
    """Return True when the bias report is clear enough to enter Paper/Tournament."""
    if report.errors:
        return False
    if treat_warnings_as_fail and report.warnings:
        return False
    return bool(report.passed)


def assert_bias_cleared(report: BiasReport, *, treat_warnings_as_fail: bool = False) -> BiasReport:
    """Raise ``BiasGateError`` unless the report passes the hard gate."""
    if not passes_bias_gate(report, treat_warnings_as_fail=treat_warnings_as_fail):
        raise BiasGateError(report)
    return report


def validate_backtest_data(df: pd.DataFrame, *, strict: bool = False, **kwargs) -> BiasReport:
    """One-shot validation: run all bias checks on a DataFrame.

    When ``strict=True``, warnings (unsorted bars, future timestamps, split jumps)
    also fail the gate — use before Tournament / MCP enrollment.
    """
    detector = LookAheadBiasDetector()
    reports = [
        detector.check_data_timestamps(df),
        detector.check_sorted_ascending(df),
        detector.validate_split_adjustment(df),
    ]
    all_warnings: list[str] = []
    all_errors: list[str] = []
    for r in reports:
        all_warnings.extend(r.warnings)
        all_errors.extend(r.errors)
    if strict:
        passed = len(all_errors) == 0 and len(all_warnings) == 0
    else:
        passed = len(all_errors) == 0
    return BiasReport(passed=passed, warnings=all_warnings, errors=all_errors)
