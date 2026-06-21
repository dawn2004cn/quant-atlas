"""Phase 55: global focus context + shareable navigation."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug

from app.modules.system.services.ui.focus_context_service import FocusContextService
from app.domain.enums import MarketCode


def test_focus_context_service_builds_share_links() -> None:
    svc = FocusContextService()
    dto = svc.build_context("600519", MarketCode.CN)
    assert dto.symbol == "600519"
    assert dto.market == "CN"
    assert dto.query_string == "symbol=600519&market=CN"
    assert len(dto.share_links) >= 4
    assert any("600519" in link.href for link in dto.share_links)


def test_focus_context_service_normalizes_cn_symbol() -> None:
    dto = FocusContextService().build_context("sh600519", MarketCode.CN)
    assert dto.symbol == "600519"


def test_focus_context_empty_symbol() -> None:
    dto = FocusContextService().build_context("", MarketCode.CN)
    assert dto.symbol == ""
    assert dto.share_links == []


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


def test_focus_context_api(app_client) -> None:
    resp = app_client.get("/api/v1/focus/context?symbol=600519&market=CN")
    assert resp.status_code == 200
    body = resp.get_json()
    data = body["data"]
    assert data["symbol"] == "600519"
    assert data["share_links"]
