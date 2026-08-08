"""Backtest domain — bias detection, validation, minute engines."""
from .bias_detector import (
    BiasGateError,
    BiasReport,
    LookAheadBiasDetector,
    assert_bias_cleared,
    passes_bias_gate,
    validate_backtest_data,
)
from .minute_engine import (
    TEN_YEAR_MINUTE_BARS,
    MinuteBacktestResult,
    run_minute_backtest,
    square_wave_signal,
    synthetic_minute_closes,
)

__all__ = [
    "LookAheadBiasDetector",
    "BiasReport",
    "BiasGateError",
    "assert_bias_cleared",
    "passes_bias_gate",
    "validate_backtest_data",
    "TEN_YEAR_MINUTE_BARS",
    "MinuteBacktestResult",
    "run_minute_backtest",
    "square_wave_signal",
    "synthetic_minute_closes",
]
