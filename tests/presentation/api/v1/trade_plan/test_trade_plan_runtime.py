"""Tests for TradePlanRuntime."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.v1.trade_plan.runtime import TradePlanRuntime


def test_adoption_service_raises_without_trade_plan():
    ctx = SimpleNamespace(
        trade_plan_service=None,
        signal_observation_service=object(),
    )
    runtime = TradePlanRuntime(ctx=ctx)
    with pytest.raises(ValidationError, match="trade_plan_service_unavailable"):
        runtime.adoption_service()


def test_adoption_service_raises_without_signal_observation():
    ctx = SimpleNamespace(
        trade_plan_service=object(),
        signal_observation_service=None,
    )
    runtime = TradePlanRuntime(ctx=ctx)
    with pytest.raises(ValidationError, match="signal_observation_service_unavailable"):
        runtime.adoption_service()
