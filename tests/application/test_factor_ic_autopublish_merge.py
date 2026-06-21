"""IC 巡检合并 autopublish.jsonl。"""

from __future__ import annotations

import json
from pathlib import Path

from app.application.services.factor_catalog_service import FactorCatalogService
from app.infrastructure.rdagent.artifact_registry import RDAgentArtifactRegistry


def test_monitor_summary_includes_autopublish_factors(tmp_path: Path) -> None:
    reg = RDAgentArtifactRegistry(tmp_path)
    reg.register_from_result("only-index", {"ok": True, "report": {"rounds": []}})

    cat = tmp_path / "config" / "factor_catalog"
    cat.mkdir(parents=True, exist_ok=True)
    row = {
        "exported_at": "2026-01-01T00:00:00Z",
        "run_id": "legacy-run",
        "artifact_id": "legacy-run::r0::task::orphan",
        "round_index": 0,
        "factor_name": "orphan",
        "factor_formulation": "Ref($close,1)",
        "metrics": {"ic_lag_1": 0.02, "ic_lag_5": 0.01},
    }
    (cat / "autopublish.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    svc = FactorCatalogService(base_dir=tmp_path)
    without = svc.monitor_summary(limit_runs=5, limit_factors=50, autopublish_tail=0)
    merged = svc.monitor_summary(limit_runs=5, limit_factors=50, autopublish_tail=20)

    assert without.get("autopublish_tail_merged") == 0
    assert merged.get("autopublish_tail_merged") == 20
    assert merged.get("factor_task_rows", 0) >= without.get("factor_task_rows", 0)

