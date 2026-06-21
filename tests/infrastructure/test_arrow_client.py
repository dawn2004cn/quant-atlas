"""Tests for Phase 10 Directive 3: ArrowComputeClient zero-copy."""
from __future__ import annotations

import numpy as np

from app.infrastructure.compute.arrow_client import ArrowComputeClient, ARROW_AVAILABLE


def _client() -> ArrowComputeClient:
    return ArrowComputeClient(use_flight=False)


def test_calculate_sma_basic():
    c = _client()
    data = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0], dtype=np.float64)
    result = c.calculate_sma(data, window=3)
    assert isinstance(result, np.ndarray)
    assert len(result) == len(data)
    assert result[2] == 11.0
    assert result[6] == 15.0


def test_calculate_sma_short_array():
    c = _client()
    data = np.array([1.0, 2.0], dtype=np.float64)
    result = c.calculate_sma(data, window=5)
    assert isinstance(result, np.ndarray)
    assert len(result) == 2


def test_calculate_ema_basic():
    c = _client()
    data = np.array([10.0, 11.0, 12.0, 13.0, 14.0], dtype=np.float64)
    result = c.calculate_ema(data, window=2)
    assert isinstance(result, np.ndarray)
    assert len(result) == len(data)


def test_calculate_atr_basic():
    c = _client()
    highs = np.array([11.0, 12.0, 13.0, 14.0, 15.0], dtype=np.float64)
    lows = np.array([9.0, 10.0, 11.0, 12.0, 13.0], dtype=np.float64)
    closes = np.array([10.5, 11.5, 12.5, 13.5, 14.5], dtype=np.float64)
    result = c.calculate_atr(highs, lows, closes, window=2)
    assert isinstance(result, np.ndarray)
    assert len(result) == len(closes)


def test_arrow_client_is_connected():
    c = _client()
    assert c.is_connected() is True


def test_arrow_availability_flag():
    assert isinstance(ARROW_AVAILABLE, bool)
