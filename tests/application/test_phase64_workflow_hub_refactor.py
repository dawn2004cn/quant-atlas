from __future__ import annotations

from types import SimpleNamespace

from app.modules.system.services.system.system_pulse_service import SystemPulseService
from app.modules.system.services.ui.decision_provenance_service import DecisionProvenanceService
from app.modules.system.services.ui.workflow_hub_service import WorkflowHubService
from app.application.workflows import WorkflowService
from app.domain.dto.decision_context_dto import DecisionContextDTO


class _MessageStore:
    enabled_backend = "memory"

    def list_recent(self, *, limit: int):
        return [
            {
                "event": "task_started",
                "task_id": "task-1",
                "task_name": "inline.basic_data_refresh",
                "label": "基础数据·同步刷新",
                "detail": "running",
                "ts": "2026-06-04T01:00:00Z",
                "meta": {},
            }
        ][:limit]


class _Facade:
    def list_capabilities(self):
        return ["fetch_bars", "run_backtest"]


class _ActiveJobTracker:
    def list_active_jobs(self, *, limit: int = 20):
        return {"items": [{"task_id": "task-1", "task_name": "inline.basic_data_refresh"}], "count": 1}


def test_workflow_hub_aggregates_runtime_context():
    workflow_service = WorkflowService()
    ctx = SimpleNamespace(
        workflow_service=workflow_service,
        active_job_tracker_service=_ActiveJobTracker(),
        tool_facade_service=_Facade(),
    )

    payload = WorkflowHubService().build_hub(ctx).model_dump()

    assert payload["active_jobs"][0]["task_id"] == "task-1"
    assert payload["capabilities"] == ["fetch_bars", "run_backtest"]
    assert [section["id"] for section in payload["sections"]] == [
        "discovery",
        "research",
        "execution",
    ]


def test_system_pulse_reports_degraded_runtime_with_remedies():
    ctx = SimpleNamespace(
        task_message_store=_MessageStore(),
        enable_celery=False,
        tdx_base_read_service=None,
        tool_facade_service=_Facade(),
        ai_analysis_service=None,
        ai_research_service=None,
        fingpt_application_service=None,
        investment_committee_service=None,
        basic_market_data_service=None,
        signal_observation_service=None,
        investment_manager_service=None,
    )

    payload = SystemPulseService().build_pulse(ctx).model_dump()

    assert payload["overall_status"] == "degraded"
    assert any(item["id"] == "celery" and item["remedy"] for item in payload["components"])


def test_decision_provenance_builds_typed_context():
    payload = DecisionProvenanceService().build_context(
        subject="CN:600519",
        input_snapshot={"price": 100.0},
        model_version="test-model",
        reasoning_trace=["momentum improved"],
        evidence=[{"source": "quote", "title": "放量上涨", "confidence": 0.8}],
    )

    assert isinstance(payload, DecisionContextDTO)
    assert payload.subject == "CN:600519"
    assert payload.evidence[0].source == "quote"
