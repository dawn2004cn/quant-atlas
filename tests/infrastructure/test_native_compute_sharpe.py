"""native_compute Sharpe alignment tests (numpy fallback path)."""

from __future__ import annotations

import numpy as np
import pytest

from app.infrastructure.compute import native_compute as nc


def test_sharpe_numpy_fallback_matches_sample_std(monkeypatch):
    monkeypatch.setattr(nc, "HAS_RUST", False)
    values = [100.0, 101.0, 99.5, 102.0, 101.0]
    arr = np.array(values, dtype=np.float64)
    returns = np.diff(arr) / arr[:-1]
    expected = float(np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252))
    assert abs(nc.calculate_sharpe_ratio(values) - expected) < 1e-9


def test_max_drawdown_positive_percent(monkeypatch):
    monkeypatch.setattr(nc, "HAS_RUST", False)
    values = [100.0, 110.0, 95.0, 105.0]
    assert nc.calculate_max_drawdown(values) == pytest.approx(13.636363636363637)
