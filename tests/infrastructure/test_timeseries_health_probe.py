from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.domain.alpha.factor_vault import InMemoryFactorVaultStorage
from app.modules.data.services.alpha_factory_orchestrator import AlphaFactoryOrchestrator


def test_lineage_nodes_include_experiment_metadata() -> None:
    vault = InMemoryFactorVaultStorage()
    vault.save_factor(
        "rank(close)",
        metadata={"experiment_id": "exp_x", "status": "submitted"},
    )
    orch = AlphaFactoryOrchestrator(factor_vault=vault, qlib_service=MagicMock())
    graph = orch.get_lineage_graph(limit=5)
    node = graph["nodes"][0]
    assert node["experiment_id"] == "exp_x"
    assert node["status"] == "submitted"
    assert node["factor_id"] == node["id"]


@patch("app.infrastructure.timeseries.ohlcv_history_reader.probe_ohlcv_tables")
@patch("app.infrastructure.timeseries.timeseries_factory.load_questdb_settings")
@patch("app.infrastructure.timeseries.timeseries_factory.load_clickhouse_settings")
def test_timeseries_health_probe_backfill_warning(
    mock_ch_cfg,
    mock_q_cfg,
    mock_probe,
) -> None:
    from app.infrastructure.timeseries.timeseries_factory import timeseries_health_probe

    mock_q_cfg.return_value = type(
        "Cfg",
        (),
        {
            "describe": lambda self: "questdb://test",
            "http_port": 9000,
            "pg_port": 8812,
            "ilp_port": 9009,
        },
    )()
    mock_ch_cfg.return_value = None
    mock_probe.return_value = {"questdb_rows": 12_000, "questdb_sample_sh600519": 0}

    class _Adapter:
        def connect(self) -> bool:
            return True

        def disconnect(self) -> None:
            return None

    with patch(
        "app.infrastructure.timeseries.timeseries_factory.create_questdb_adapter",
        return_value=_Adapter(),
    ):
        out = timeseries_health_probe()

    assert out["warnings"]
    assert "questdb_backfill_recommended" in out["warnings"]
    assert "questdb_sample_sparse" in out["warnings"]
    assert "celery_beat" in out
    assert out["celery_beat"].get("schedule_label")
    assert "backfill" in out
    assert out["backfill"]["target_rows"] == 1_000_000
    assert "execution" in out
    assert out["execution"]["qmt"].get("execution_mode") in (
        "disabled",
        "simulation",
        "live",
    )
