"""FactorCatalogService.monitor_summary 聚合逻辑。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.application.services.factor_catalog_service import FactorCatalogService


def test_monitor_summary_counts_weak_ic() -> None:
    svc = FactorCatalogService(base_dir=Path("."))
    fake = {
        "factors": [
            {
                "kind": "factor_task",
                "factor_name": "weak_f",
                "run_id": "r1",
                "artifact_id": "a1",
                "ic_decay": [{"lag": 1, "ic": 0.02}],
            },
            {
                "kind": "factor_task",
                "factor_name": "ok_f",
                "run_id": "r1",
                "artifact_id": "a2",
                "ic_decay": [{"lag": 1, "ic": 0.12}],
            },
            {"kind": "factor_code", "factor_name": "skip", "ic_decay": [{"lag": 1, "ic": 0.01}]},
        ],
        "runs_index": [{"run_id": "r1"}],
    }
    with patch.object(svc, "list_factors", return_value=fake):
        out = svc.monitor_summary(ic_warn_threshold=0.05, limit_runs=10, limit_factors=50)
    assert out["weak_ic_lag1_count"] == 1
    assert out["factors_with_ic_decay"] == 2
    assert out["mean_abs_ic_lag1"] is not None
    assert abs(out["mean_abs_ic_lag1"] - 0.07) < 1e-6
    assert len(out["alerts"]) == 1
    assert out["alerts"][0]["code"] == "low_ic_lag1"
