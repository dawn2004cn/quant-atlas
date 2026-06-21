from __future__ import annotations

"""Phase 36: SDK facade for attribution, alerts, and strategy snapshots."""

from pathlib import Path

import pytest

from app.modules.system.services.system.alert_center_service import AlertCenterService
from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService
from app.infrastructure.repositories.file_strategy_snapshot_repository import FileStrategySnapshotRepository
from app.sdk import QuantAtlasClient, create_client
from app.sdk.facades.alerts import AlertsFacade
from app.sdk.facades.attribution import AttributionFacade
from app.sdk.facades.snapshots import SnapshotsFacade


class _FakeAlertStore:
    def list_recent(self, *, limit: int = 80) -> list[dict]:
        return [
            {
                "id": "1",
                "ts": "2026-05-23T10:00:00Z",
                "event": "factor_ic_alert",
                "task_id": "ic-1",
                "task_name": "factor_ic_monitor_tick",
                "label": "IC",
                "detail": "weak factors",
                "meta": {},
            }
        ][:limit]


def test_attribution_facade_builds_report() -> None:
    facade = AttributionFacade()
    report = facade.report(
        strategy_name="demo",
        period="30d",
        positions=[{"symbol": "600519", "name": "茅台", "value": 100000, "return_pct": 2.0}],
        include_slippage=False,
    )
    assert report.strategy_name == "demo"
    payload = facade.report_dict(
        strategy_name="demo",
        period="30d",
        positions=[{"symbol": "600519", "name": "茅台", "value": 100000, "return_pct": 2.0}],
        factor_exposures={"momentum": 0.2},
        factor_returns={"momentum": 0.05},
        include_slippage=False,
    )
    assert payload["strategy_name"] == "demo"
    assert len(payload["style_contributions"]) >= 1


def test_alerts_facade_lists_and_summarizes() -> None:
    service = AlertCenterService(
        message_store_factory=lambda: _FakeAlertStore(),
        freshness_checker=lambda _table, _minutes=15: True,
    )
    facade = AlertsFacade(service)
    feed = facade.list(include_system_probes=False)
    assert feed.total >= 1
    summary = facade.summary()
    assert "warning_count" in summary


def test_snapshots_facade_capture_and_rollback(tmp_path: Path) -> None:
    repo = FileStrategySnapshotRepository(tmp_path / "snapshots")
    service = StrategySnapshotService(
        repository=repo,
        repo_root=tmp_path,
        freshness_checker=lambda _table, _minutes=15: True,
    )
    facade = SnapshotsFacade(service)
    snap = facade.capture(strategy_name="alpha", label="v1")
    assert snap.strategy_name == "alpha"
    rows = facade.list(strategy_name="alpha")
    assert len(rows) == 1
    result = facade.rollback(snap.id)
    assert result.active is True


def test_quant_atlas_client_exposes_facades(tmp_path: Path) -> None:
    repo = FileStrategySnapshotRepository(tmp_path / "snapshots")
    snapshot_service = StrategySnapshotService(
        repository=repo,
        repo_root=tmp_path,
        freshness_checker=lambda _table, _minutes=15: True,
    )
    alert_service = AlertCenterService(
        message_store_factory=lambda: _FakeAlertStore(),
        freshness_checker=lambda _table, _minutes=15: True,
    )
    client = create_client(
        snapshot_service=snapshot_service,
        alert_service=alert_service,
    )
    assert isinstance(client, QuantAtlasClient)
    assert client.attribution.report(
        strategy_name="x",
        period="7d",
        positions=[{"symbol": "000001", "value": 1, "return_pct": 0.0}],
        include_slippage=False,
    ).strategy_name == "x"
    assert client.alerts.summary()["total"] >= 0
    assert client.snapshots.capture(strategy_name="sdk_test").strategy_name == "sdk_test"


def test_run_strategy_requires_swarm() -> None:
    client = QuantAtlasClient()
    with pytest.raises(RuntimeError, match="swarm_service_not_configured"):
        client.run_strategy(lambda: None, "600519")
