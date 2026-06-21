"""Phase 62: unified UX decision-flow contract."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug

from app.modules.system.services.ui.decision_flow_contract_service import (
    DecisionFlowContractService,
)


def test_decision_flow_contract_lists_all_optimized_links() -> None:
    contract = DecisionFlowContractService().build_contract(market="CN", symbol="600519")
    entry_ids = {item["id"] for item in contract["entrypoints"]}
    probe_ids = {item["id"] for item in contract["self_check_probes"]}

    assert {
        "search_discovery",
        "stock_evidence",
        "strategy_sandbox",
        "phased_feedback",
        "predictive_preload",
    } <= entry_ids
    assert {
        "timeseries_health",
        "realtime_status",
        "execution_manifest",
        "integration_stack",
        "timeseries_sync_history",
    } <= probe_ids
    assert "evidence_timeline" in {item["type"] for item in contract["component_types"]}
    assert "decision-brief" in contract["entrypoints"][1]["endpoints"]["brief"]


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


def test_decision_flow_contract_api(app_client) -> None:
    resp = app_client.get("/api/v1/ux/decision-flow?market=CN&symbol=600519")

    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data["version"] == "2026-05-ux-decision-flow-v2"
    assert any(item["id"] == "strategy_sandbox" for item in data["entrypoints"])


def test_timeseries_sync_history_api(app_client) -> None:
    resp = app_client.get(
        "/api/v1/data/timeseries-sync-history?limit=5&source=celery_beat"
    )
    assert resp.status_code == 200
    payload = (resp.get_json() or {}).get("data") or {}
    assert "runs" in payload
    assert isinstance(payload["runs"], list)
    assert payload.get("limit") == 5


def test_static_ux_helpers_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "static" / "js" / "decision_brief.js").is_file()
    assert (root / "static" / "js" / "predictive_preload.js").is_file()
