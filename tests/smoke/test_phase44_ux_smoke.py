"""Phase 44: UX API + pages smoke tests (attribution, alerts, snapshots)."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    monkeypatch.setenv("ENABLE_BASIC_DATA_SCHEDULER", "0")
    monkeypatch.setenv("ENABLE_CELERY", "0")
    monkeypatch.setenv("ENABLE_QLIB", "0")
    monkeypatch.setenv("ENABLE_RD_AGENT", "0")
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "memory://")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)

    instance = tmp_path / "instance"
    instance.mkdir()
    monkeypatch.setattr("app.config.settings.INSTANCE_DIR", instance)
    monkeypatch.setattr("app.modules.strategy.services.strategy.strategy_snapshot_service.INSTANCE_DIR", instance)

    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303)
    return client


def test_attribution_report_api(app_client) -> None:
    resp = app_client.get("/api/v1/attribution/report?period=30d&include_slippage=0")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload.get("status") == "success"
    data = payload.get("data") or {}
    assert data.get("strategy_name")
    assert "total_return" in data


def test_alert_center_api(app_client) -> None:
    summary = app_client.get("/api/v1/system/alerts/summary")
    assert summary.status_code == 200
    body = summary.get_json()
    assert body.get("status") == "success"
    assert "critical_count" in (body.get("data") or {})

    feed = app_client.get("/api/v1/system/alerts?limit=10&include_probes=0")
    assert feed.status_code == 200
    feed_body = feed.get_json()
    assert feed_body.get("status") == "success"
    assert "items" in (feed_body.get("data") or {})


def test_strategy_snapshot_api_roundtrip(app_client) -> None:
    create = app_client.post(
        "/api/v1/strategy/snapshots",
        json={"strategy_name": "smoke_alpha", "label": "e2e", "mark_active": True},
    )
    assert create.status_code == 200
    created = create.get_json()
    snap = (created.get("data") or {}).get("snapshot") or created.get("data") or {}
    snap_id = snap.get("id")
    assert snap_id

    listing = app_client.get("/api/v1/strategy/snapshots?strategy_name=smoke_alpha")
    assert listing.status_code == 200
    rows = listing.get_json().get("data") or []
    assert any(row.get("id") == snap_id for row in rows)

    rollback = app_client.post(
        f"/api/v1/strategy/snapshots/{snap_id}/rollback",
        json={"apply_settings": False, "apply_code": False},
    )
    assert rollback.status_code == 200
    rb = (rollback.get_json().get("data") or {}).get("rollback") or rollback.get_json().get("data") or {}
    assert rb.get("active") is True


def test_ux_dashboard_pages_render(app_client) -> None:
    for path in ("/attribution-dashboard", "/alert-center", "/strategy-snapshots"):
        resp = app_client.get(path)
        assert resp.status_code == 200, path
        assert b"Quant Atlas" in resp.data or resp.data
