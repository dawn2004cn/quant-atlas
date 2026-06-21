"""Critical route smoke — boot app and hit key tier/compliance endpoints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import werkzeug


def _seed_test_users(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "admin": {
            "id": 1,
            "password": hashlib.sha256(b"admin123").hexdigest(),
            "role": "admin",
            "wechat_openid": None,
            "display_name": "Admin",
            "avatar_url": None,
        }
    }
    (config_dir / "users.json").write_text(json.dumps(payload), encoding="utf-8")


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
    config_dir = tmp_path / "config"
    _seed_test_users(config_dir)
    monkeypatch.setattr("app.config.settings.CONFIG_DIR", config_dir)
    monkeypatch.setattr("app.config.CONFIG_DIR", config_dir)

    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303), login.get_data(as_text=True)[:500]
    return client


def test_system_health(app_client) -> None:
    resp = app_client.get("/api/v1/system/health")
    assert resp.status_code == 200


def test_optimization_budget_wiring(app_client) -> None:
    resp = app_client.get("/api/v1/optimization/budget/validate-wiring")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("ok") is True
    assert body.get("success") is True
    data = body.get("data") or {}
    assert data.get("factory_count", 0) > 0


def test_federated_status(app_client) -> None:
    resp = app_client.get("/api/v1/user-tiers/institution/federated/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("ok") is True
    assert body.get("success") is True
    data = body.get("data") or {}
    assert "total_nodes" in data


def test_realtime_ticks_status(app_client) -> None:
    resp = app_client.get("/api/v1/realtime/ticks/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("status") == "success" or body.get("ok") is True


def test_trading_preflight_post(app_client) -> None:
    resp = app_client.post(
        "/api/v1/trading/preflight",
        json={"symbol": "600519", "direction": "BUY", "price": 100, "quantity": 10},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("status") == "success" or body.get("ok") is True
    assert "data" in body
