"""Phase 25: TDX base read service, hot sector registration, async decay task."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.modules.data.services.tdx_base_read_service import TdxBaseReadService
from app.modules.data.services.forward_testing_service import FactorDecayMonitor


class _FakeBlockPort:
    def list_blocks_simple(self, *, block_kind: str | None = None) -> list[dict[str, Any]]:
        assert block_kind == "gn"
        return [{"block_kind": "gn", "block_name": "测试", "updated_at": "2026-01-01"}]

    def load_members_bulk(
        self,
        block_keys: list[tuple[str, str]],
        *,
        per_block_limit: int,
    ) -> dict[tuple[str, str], list[dict[str, str]]]:
        return {("gn", "测试"): [{"symbol": "600519", "name": "茅台"}]}

    def list_symbol_blocks(self, symbols: list[str]) -> list[dict[str, Any]]:
        return [{"block_kind": "gn", "block_name": "测试", "updated_at": "2026-01-01"}]

    def list_watchlists(self) -> list[dict[str, Any]]:
        return [{"name": "自选", "source_path": "/x.blk", "updated_at": "2026-01-01"}]

    def list_watchlist_members(self, *, watchlist_name: str) -> list[dict[str, Any]]:
        return [{"symbol": "600519", "name": "茅台"}]

    def get_latest_finance_snapshot(self, symbol: str) -> dict[str, Any] | None:
        return {"symbol": symbol, "report_date": "2025-12-31"}


def test_tdx_base_read_service_delegates_to_block_port(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.use_mysql = True
    settings.mysql = object()
    monkeypatch.setattr(
        "app.modules.data.services.tdx_base_read_service.require_tdx_block_read_port",
        lambda: _FakeBlockPort(),
    )
    svc = TdxBaseReadService(settings=settings)
    blocks = svc.list_blocks(block_kind="gn")
    assert blocks[0]["block_name"] == "测试"
    members = svc.list_block_members(block_kind="gn", block_name="测试", limit=10)
    assert members[0]["symbol"] == "600519"


def test_factor_decay_monitor_enqueues_async_log_task(monkeypatch: pytest.MonkeyPatch) -> None:
    queued: list[dict[str, Any]] = []

    class _AsyncRepo:
        def get_factor(self, factor_id: str) -> dict[str, Any]:
            return {"factor_id": factor_id, "ir": 0.2, "ic_mean": 0.01, "decay_rate": 0.1}

        async def log_decay_event(self, **kwargs: Any) -> int:
            return 1

    class _FakeTask:
        @staticmethod
        def delay(payload: dict[str, Any]) -> None:
            queued.append(payload)

    monkeypatch.setattr(
        "app.tasks.factor_decay_tasks.log_factor_decay_event_task",
        _FakeTask,
    )
    monitor = FactorDecayMonitor(_AsyncRepo(), ir_threshold=0.5)
    assert monitor.check_decay("alpha1") is True
    assert queued
    assert queued[0]["factor_id"] == "alpha1"
    assert queued[0]["severity"] == "critical"
