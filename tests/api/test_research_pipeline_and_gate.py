"""研究闭环快照、RD bundle qlib_gate、pipeline API 登录保护。"""

from pathlib import Path
from unittest.mock import MagicMock

import werkzeug

from app.application.services.qlib_pipeline_service import QlibPipelineService
from app.application.services.research_pipeline_snapshot import (
    _summarize_qlib_gate,
    build_research_pipeline_snapshot,
)
from app.domain.enums import MarketCode
from app.infrastructure.rdagent.artifact_registry import RDAgentArtifactRegistry
from app.modules.system.services.tools.tool_facade_service import ToolFacadeService


def test_summarize_qlib_gate_includes_factor_expression() -> None:
    g = {
        "ok": True,
        "skipped": False,
        "reference_symbol": "000300",
        "factor_expression_gate": {
            "ok": True,
            "skipped": False,
            "formulation_preview": "Mean($close,5)",
        },
    }
    s = _summarize_qlib_gate(g)
    assert s is not None
    assert s["overall_ok"] is True
    assert s["factor_expression"]["ok"] is True


def test_merge_qlib_gate_writes_bundle(tmp_path: Path):
    reg = RDAgentArtifactRegistry(tmp_path)
    reg.register_from_result("job-a", {"ok": True, "report": {"rounds": []}})
    reg.merge_qlib_gate("job-a", {"ok": False, "skipped": True, "message": "test skip"})
    b = reg.get_run_bundle("job-a")
    assert b is not None
    assert b.get("qlib_gate", {}).get("skipped") is True
    assert b["qlib_gate"].get("checked_at")


def test_build_research_pipeline_snapshot_steps(tmp_path: Path):
    m = MagicMock()

    def fake_fetch_daily_bars(sym, market, *, period="2y"):
        return [
            {"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.0, "volume": 1000},
        ], "test_bars"

    m.fetch_daily_bars.side_effect = fake_fetch_daily_bars
    qlib_svc = QlibPipelineService(m, base_dir=tmp_path)
    qlib_svc.ingest_symbols(["600519"], MarketCode.US, period="5d")

    rd = MagicMock()
    rd.list_recent_runs.return_value = []

    snap = build_research_pipeline_snapshot(
        enable_qlib=True,
        enable_rd_agent=True,
        qlib_pipeline_service=qlib_svc,
        rdagent_run_service=rd,
    )
    assert snap["enable_qlib"] is True
    assert len(snap["steps"]) >= 5
    assert any(s["id"] == "data_csv" for s in snap["steps"])


def test_pipeline_status_requires_login(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)
    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    r = c.get("/api/v1/research/pipeline-status")
    assert r.status_code in (302, 401)


def test_pipeline_status_ok_when_logged_in(monkeypatch):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)
    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    assert c.post("/login", data={"username": "admin", "password": "admin123"}).status_code in (302, 303)
    r = c.get("/api/v1/research/pipeline-status")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") == "success"
    assert "data" in body
    assert "steps" in body["data"]
