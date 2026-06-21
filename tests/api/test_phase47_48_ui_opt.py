"""Phase 47/48: actionable API errors + global health indicator."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug

from app.application.errors import ValidationError
from app.presentation.api.actionable_error_catalog import enrich_error_payload, resolve_actionable_hints
from app.presentation.api.error_handlers import map_validation_error


def test_resolve_actionable_hints_market_service() -> None:
    hints = resolve_actionable_hints(code="validation_error", message="market_service_unavailable")
    assert hints
    assert hints[0]["action_href"] == "/integration-hub"


def test_enrich_error_payload_attaches_hints() -> None:
    payload = enrich_error_payload(
        {
            "status": "error",
            "error": {"code": "unauthorized", "message": "Authentication required", "details": {}},
        }
    )
    assert payload["error"]["hints"][0]["action_label"] == "去登录"


def test_map_validation_error_includes_hints() -> None:
    payload, status = map_validation_error(ValidationError("symbol_required"))
    assert status == 400
    assert payload["error"]["hints"]


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


def test_health_banner_api(app_client) -> None:
    resp = app_client.get("/api/v1/system/health-banner")
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data.get("level") in ("ok", "warning", "critical")
    assert "allow_live_trading" in data


def test_base_page_includes_health_indicator(app_client) -> None:
    resp = app_client.get("/")
    assert resp.status_code == 200
    assert b"qcHealthIndicator" in resp.data
    assert b"api_error_banner.js" in resp.data


def test_api_validation_error_returns_hints(app_client) -> None:
    resp = app_client.get("/api/v1/system/alerts?min_level=bad_level")
    assert resp.status_code == 400
    err = (resp.get_json() or {}).get("error") or {}
    assert err.get("hints")
