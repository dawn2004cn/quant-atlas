"""RiskGuardService application-layer checks (REQ-SRS-01)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.domain.trading.risk_guard import RiskGuardDecision
from app.modules.execution.services.risk_guard_service import (
    AccountRiskSnapshot,
    InMemoryRiskGuardStore,
    RiskGuardBlockedError,
    RiskGuardService,
)


@dataclass
class _FakeActions:
    flattened: list[tuple[str, str]] = field(default_factory=list)
    suspended: list[tuple[str, str]] = field(default_factory=list)
    alerts: list[tuple[str, RiskGuardDecision]] = field(default_factory=list)

    def flatten_all(self, account_id: str, reason: str) -> None:
        self.flattened.append((account_id, reason))

    def suspend_execution(self, account_id: str, reason: str) -> None:
        self.suspended.append((account_id, reason))

    def alert(self, account_id: str, decision: RiskGuardDecision) -> None:
        self.alerts.append((account_id, decision))


def test_check_before_order_allows_when_healthy():
    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "acc1",
        AccountRiskSnapshot(equity=99_000.0, day_start_equity=100_000.0, consecutive_stop_outs=1),
    )
    svc = RiskGuardService(store=store, actions=_FakeActions())
    d = svc.check_before_order("acc1")
    assert d.action == "allow"
    assert d.block_new_orders is False


def test_check_before_order_blocks_when_suspended_flag():
    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "acc1",
        AccountRiskSnapshot(
            equity=100_000.0,
            day_start_equity=100_000.0,
            consecutive_stop_outs=0,
            execution_suspended=True,
        ),
    )
    svc = RiskGuardService(store=store, actions=_FakeActions())
    d = svc.check_before_order("acc1")
    assert d.block_new_orders is True
    assert d.action == "suspend_execution"


def test_on_decision_flatten_calls_actions_and_suspends_flag():
    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "acc1",
        AccountRiskSnapshot(equity=94_000.0, day_start_equity=100_000.0, consecutive_stop_outs=0),
    )
    actions = _FakeActions()
    svc = RiskGuardService(store=store, actions=actions)
    d = svc.check_before_order("acc1")
    assert d.action == "flatten_all"
    svc.on_decision("acc1", d)
    assert actions.flattened and actions.alerts
    assert store.get_snapshot("acc1").execution_suspended is True


def test_ensure_order_allowed_raises():
    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "acc1",
        AccountRiskSnapshot(equity=94_000.0, day_start_equity=100_000.0, consecutive_stop_outs=0),
    )
    svc = RiskGuardService(store=store, actions=_FakeActions())
    with pytest.raises(RiskGuardBlockedError):
        svc.ensure_order_allowed("acc1")
