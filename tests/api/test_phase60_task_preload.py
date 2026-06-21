"""Phase 60: phased task feedback and predictive preload plans."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import werkzeug

from app.modules.system.services.system.task_feedback_service import TaskFeedbackService
from app.modules.system.services.system.task_phase_plan_service import TaskPhasePlanService
from app.modules.system.services.ui.predictive_preload_service import PredictivePreloadService


class FakeHotSectorStorage:
    def resolve_members(self, sector_code: str, **kwargs):
        assert sector_code == "BK001"
        return (
            [
                {"symbol": "sh600519", "name": "Kweichow Moutai", "sector_name": "Liquor"},
                {"stock_code": "sz000858", "stock_name": "Wuliangye", "sector_name": "Liquor"},
            ],
            "mysql",
        )


def test_task_phase_plan_matches_sync_template() -> None:
    payload = TaskPhasePlanService().build_progress(
        task_name="app.tasks.data_backfill_tasks.sync_incremental_tdx",
        state="STARTED",
    )

    assert payload["phase_source"] == "template"
    assert payload["steps"][0] == "Fetch market data"
    assert payload["current_step_key"] == "fetch"


def test_task_feedback_includes_step_details() -> None:
    svc = TaskFeedbackService(message_store_factory=lambda: object())
    with patch(
        "app.modules.system.services.system.task_feedback_service.get_celery_task_status",
        return_value={"ok": True, "state": "STARTED", "ready": False, "successful": False, "failed": False},
    ):
        fb = svc.build_feedback(
            "tid-phase",
            task_name="app.tasks.qlib_data_update.mysql_to_qlib_full_sync",
        )

    assert fb["phase_source"] == "template"
    assert fb["step_details"]
    assert fb["current_step"]
    assert fb["next_step"]


def test_predictive_preload_service_builds_prefetch_urls() -> None:
    payload = PredictivePreloadService(
        hot_sector_storage_service=FakeHotSectorStorage()
    ).build_sector_plan(sector_code="BK001", market="CN", limit=2)

    assert [item["symbol"] for item in payload["candidates"]] == ["600519", "000858"]
    assert payload["prefetch"][0]["urls"][0] == "/api/v1/stocks/CN/600519"
    assert "attribution-timeline" in payload["prefetch"][0]["urls"][1]


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


def test_task_phase_plan_api(app_client) -> None:
    resp = app_client.get(
        "/api/v1/system/task-phase-plan?task_name=app.tasks.news_backfill_tasks.scheduled_news_daily"
    )
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data["phase_source"] == "template"
    assert data["steps"][0] == "Collect evidence"
