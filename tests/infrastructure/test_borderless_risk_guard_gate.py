"""Borderless router rejects orders when Risk Guard blocks."""

from __future__ import annotations

import pytest

from app.domain.execution.driver_protocol import OrderStatus, TradeRequest
from app.infrastructure.execution.borderless_router import BorderlessExecutionRouter
from app.modules.execution.services.risk_guard_service import (
    AccountRiskSnapshot,
    InMemoryRiskGuardStore,
    RiskGuardService,
)


@pytest.mark.asyncio
async def test_submit_order_rejected_when_drawdown_breach():
    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "acc1",
        AccountRiskSnapshot(equity=90_000.0, day_start_equity=100_000.0, consecutive_stop_outs=0),
    )
    guard = RiskGuardService(store=store)
    router = BorderlessExecutionRouter(risk_guard=guard)
    resp = await router.submit_order(
        TradeRequest(symbol="AAPL", metadata={"account_id": "acc1", "market": "US"}),
    )
    assert resp.status == OrderStatus.REJECTED
    assert "risk_guard_blocked" in resp.message
