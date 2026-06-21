"""qlib_gate：优先使用 bundle.benchmark（mock，无 pyqlib）。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.infrastructure.rdagent import qlib_gate as qg


def test_execute_rdagent_qlib_gate_uses_bundle_benchmark(tmp_path: Path) -> None:
    job_id = "run-test-1"
    bundle = {
        "run_id": job_id,
        "benchmark": "SH000300",
        "artifacts": [
            {
                "kind": "factor_task",
                "artifact_id": f"{job_id}::r0::task::m",
                "round_index": 0,
                "factor_name": "m",
                "factor_formulation": "Mean($close, 3)",
                "metrics": {"ic_lag_1": 0.01},
            }
        ],
    }
    mock_reg = MagicMock()
    mock_reg.get_run_bundle.return_value = bundle

    mock_svc = MagicMock()
    mock_svc.status.return_value = {"last_meta": {"instruments": ["SH600519"]}, "instruments_on_disk": []}
    mock_svc.unified_buy_hold_backtest.return_value = {
        "error": None,
        "metrics": {"total_return": 0.01, "max_drawdown": -0.02, "sharpe_ratio": 0.5},
        "backtest_engine": "mock",
        "source": "mock",
    }

    with (
        patch.object(qg, "RDAgentArtifactRegistry", return_value=mock_reg),
        patch(
            "app.infrastructure.repositories.deps.create_default_qlib_pipeline_service",
            return_value=mock_svc,
        ),
    ):
        out = qg.execute_rdagent_qlib_gate(job_id, base_dir=tmp_path)

    assert out.get("reference_kind") == "benchmark"
    assert isinstance(out.get("factor_expression_gate"), dict)
    assert out["factor_expression_gate"].get("ok") is True
    mock_svc.unified_buy_hold_backtest.assert_called_once()
    sym_arg = mock_svc.unified_buy_hold_backtest.call_args[0][0]
    assert sym_arg == "000300"

