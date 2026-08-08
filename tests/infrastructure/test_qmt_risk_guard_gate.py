"""QMT executor honors Risk Guard before submit."""

from __future__ import annotations

import pytest

from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.infrastructure.execution.qmt_executor import QMTExecutor
from app.modules.execution.services.risk_guard_service import (
    AccountRiskSnapshot,
    InMemoryRiskGuardStore,
    RiskGuardBlockedError,
    RiskGuardService,
)


def test_qmt_execute_blocked_by_risk_guard(monkeypatch):
    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "qmt_acc",
        AccountRiskSnapshot(equity=90_000.0, day_start_equity=100_000.0),
    )
    guard = RiskGuardService(store=store)

    monkeypatch.setenv("RISK_GUARD_ENABLED", "1")
    monkeypatch.setattr(
        "app.modules.execution.services.risk_guard_factory.get_risk_guard_service",
        lambda **kwargs: guard,
    )
    monkeypatch.setattr(
        "app.modules.execution.services.risk_guard_factory.risk_guard_enabled",
        lambda: True,
    )

    exe = QMTExecutor(account_id="qmt_acc", qmt_path="C:/fake/qmt", live_submit=False)
    signal = TradeSignalDTO(
        symbol="600519",
        direction=SignalDirection.BUY,
        price=100.0,
        quantity=100,
        strategy_id="test",
    )
    with pytest.raises(RiskGuardBlockedError):
        exe.execute(signal)
