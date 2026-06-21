"""Smoke tests for agent backtest engine base module."""

from __future__ import annotations


def test_base_engine_imports_quality_gate():
    from backtest.engines.base import BaseEngine
    from backtest.validation_gate import MarketDataQualityGate

    assert issubclass(BaseEngine, object)
    assert MarketDataQualityGate is not None
