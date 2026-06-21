"""AkShare loader adjustment policy for backtests."""

from __future__ import annotations

import app.core.runtime_config as runtime_config
from app.infrastructure.agent.backtest.loaders import akshare_loader as mod


def test_backtest_adjust_defaults_to_hfq(monkeypatch):
    monkeypatch.delenv("AKSHARE_BACKTEST_ADJUST", raising=False)
    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)
    assert mod._backtest_adjust() == "hfq"


def test_backtest_adjust_respects_env(monkeypatch):
    monkeypatch.setenv("AKSHARE_BACKTEST_ADJUST", "none")
    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)
    assert mod._backtest_adjust() == ""
