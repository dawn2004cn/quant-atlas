"""Alpha factory orchestrator helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.domain.alpha.factor_vault import InMemoryFactorVaultStorage
from app.modules.data.services.alpha_factory_orchestrator import (
    AlphaFactoryOrchestrator,
    _factor_display_ic,
)


def test_factor_display_ic_prefers_metadata_ic() -> None:
    ic, proxy = _factor_display_ic({"metadata": {"ic": 0.042}, "sharpe_ratio": 1.5})
    assert ic == 0.042
    assert proxy is False


def test_factor_display_ic_falls_back_to_sharpe_proxy() -> None:
    ic, proxy = _factor_display_ic({"sharpe_ratio": 1.1})
    assert ic == 1.1
    assert proxy is True


def test_extract_ic_from_nested_metrics() -> None:
    from app.modules.data.services.alpha_factory_orchestrator import _extract_ic_from_payload

    assert _extract_ic_from_payload({"metrics": {"ic_mean": 0.031}}) == 0.031


def test_get_lineage_graph_ic_proxy_flag() -> None:
    vault = InMemoryFactorVaultStorage()
    fid = vault.save_factor("rank(close)", sharpe_ratio=0.8, metadata={"ic": 0.03})
    orch = AlphaFactoryOrchestrator(factor_vault=vault, qlib_service=MagicMock())
    graph = orch.get_lineage_graph(limit=10)
    node = next(n for n in graph["nodes"] if n["id"] == fid)
    assert node["ic"] == 0.03
    assert node["ic_proxy"] is False


def test_analyze_experiment_result_persists_ic() -> None:
    from app.domain.ports.qlib_task_ports import QlibExperimentResult

    vault = InMemoryFactorVaultStorage()
    qlib = MagicMock()
    qlib.get_experiment_result.return_value = QlibExperimentResult(
        experiment_id="exp_1",
        status="completed",
        formula="rank(close)",
        backtest_result={"sharpe_ratio": 1.2, "max_drawdown": 0.08, "ic": 0.045},
    )
    orch = AlphaFactoryOrchestrator(factor_vault=vault, qlib_service=qlib)
    res = orch.analyze_experiment_result("exp_1")
    assert res["status"] == "success"
    assert res["ic"] == 0.045
    saved = vault.list_recent_factors(limit=1)[0]
    assert saved["metadata"]["ic"] == 0.045


def test_submit_then_analyze_updates_same_vault_factor() -> None:
    from app.domain.ports.qlib_task_ports import QlibExperimentResult

    vault = InMemoryFactorVaultStorage()
    qlib = MagicMock()
    qlib.submit_experiment.return_value = "exp_merge"
    qlib.get_experiment_result.return_value = QlibExperimentResult(
        experiment_id="exp_merge",
        status="completed",
        formula="rank(volume)",
        backtest_result={"sharpe_ratio": 1.4, "max_drawdown": 0.06, "ic": 0.052},
    )
    orch = AlphaFactoryOrchestrator(factor_vault=vault, qlib_service=qlib)

    submit = orch.submit_factor_experiment(
        "rank(volume)",
        data_scope={"market": "CN"},
        save_to_vault=True,
    )
    assert submit["factor_id"]
    assert vault.list_recent_factors(limit=10)[0]["metadata"]["status"] == "submitted"

    analyzed = orch.analyze_experiment_result("exp_merge")
    assert analyzed["factor_id"] == submit["factor_id"]
    assert analyzed["ic"] == 0.052
    assert len(vault.list_recent_factors(limit=10)) == 1
    final = vault.get_factor(submit["factor_id"])
    assert final is not None
    assert final["metadata"]["status"] == "completed"
    assert final["metadata"]["ic"] == 0.052
    assert final["metadata"]["data_scope"] == {"market": "CN"}


def test_evolve_factor_targeted_dispatches_job() -> None:
    vault = InMemoryFactorVaultStorage()
    factor_id = vault.save_factor("close/open-1", sharpe_ratio=1.0)
    orch = AlphaFactoryOrchestrator(factor_vault=vault, qlib_service=MagicMock())

    with patch(
        "app.modules.data.services.alpha_factory_orchestrator._dispatch_rdagent_evolution",
        return_value={"job_id": "job_test_01", "execution_mode": "thread"},
    ) as dispatch:
        res = orch.evolve_factor_targeted(factor_id)

    assert res["ok"] is True
    assert res["job_id"] == "job_test_01"
    dispatch.assert_called_once()
