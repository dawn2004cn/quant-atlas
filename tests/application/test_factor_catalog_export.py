"""config/factor_catalog/autopublish.jsonl 导出。"""

from __future__ import annotations

import json
from pathlib import Path

from app.application.services.factor_catalog_service import FactorCatalogService
from app.infrastructure.rdagent.artifact_registry import RDAgentArtifactRegistry
from app.infrastructure.rdagent.factor_catalog_export import append_factor_tasks_from_bundle


def test_append_factor_tasks_dedupes_by_artifact_id(tmp_path: Path) -> None:
    reg = RDAgentArtifactRegistry(tmp_path)
    run_id = "rid-1"
    result = {
        "ok": True,
        "provider_uri": str(tmp_path / "bin"),
        "benchmark": "SH000300",
        "market": "csi300",
        "loop_n": 1,
        "report": {
            "round_count": 1,
            "rounds": [
                {
                    "tasks": [
                        {
                            "factor_name": "alpha",
                            "factor_formulation": "Rank($close)",
                            "factor_description": "d",
                        }
                    ],
                    "qlib_metrics_series": {"ic_lag_1": 0.1},
                }
            ],
        },
    }
    reg.register_from_result(run_id, result)

    r1 = append_factor_tasks_from_bundle(base_dir=tmp_path, run_id=run_id)
    assert r1.get("appended") == 1
    r2 = append_factor_tasks_from_bundle(base_dir=tmp_path, run_id=run_id)
    assert r2.get("appended") == 0

    jlp = tmp_path / "config" / "factor_catalog" / "autopublish.jsonl"
    lines = [ln for ln in jlp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["artifact_id"].endswith("alpha")
    assert row["factor_formulation"].startswith("Rank")

    snap = FactorCatalogService(base_dir=tmp_path).list_autopublish_tail(limit=10)
    assert snap.get("total") == 1
    assert snap["records"][0]["run_id"] == run_id

