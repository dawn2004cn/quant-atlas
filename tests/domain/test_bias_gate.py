"""Bias hard gate for tournament / MCP enrollment."""

from __future__ import annotations

import pandas as pd
import pytest

from app.domain.backtest.bias_detector import (
    BiasGateError,
    BiasReport,
    LookAheadBiasDetector,
    assert_bias_cleared,
    passes_bias_gate,
    validate_backtest_data,
)


def test_passes_bias_gate_fails_on_errors():
    report = BiasReport(passed=False, errors=["look-ahead"])
    assert passes_bias_gate(report) is False


def test_passes_bias_gate_ok_when_clean():
    assert passes_bias_gate(BiasReport(passed=True)) is True


def test_assert_bias_cleared_raises():
    with pytest.raises(BiasGateError):
        assert_bias_cleared(BiasReport(passed=False, errors=["x"]))


def test_validate_strict_fails_on_unsorted_warnings():
    df = pd.DataFrame({"date": pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02"]), "close": [1, 2, 3]})
    report = validate_backtest_data(df, strict=True)
    assert report.passed is False
    assert report.warnings


def test_signal_alignment_error():
    det = LookAheadBiasDetector()
    report = det.check_signal_vs_data_alignment("2024-02-01", "2024-01-31")
    assert report.passed is False
    with pytest.raises(BiasGateError):
        assert_bias_cleared(report)
