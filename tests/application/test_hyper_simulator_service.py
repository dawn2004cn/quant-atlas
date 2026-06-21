from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.execution.services.hyper_simulator_service import HyperSimulatorService
from app.domain.simulation.hyper_sim_schema import HyperSimRunRequest
from app.domain.simulation.monte_carlo_engine import monte_carlo_permutation, simulate_gbm_paths


def test_monte_carlo_permutation_significance() -> None:
    pnls = [1200.0, -400.0, 800.0, 600.0, -200.0, 1500.0]
    out = monte_carlo_permutation(pnls, initial_capital=100_000.0, n_simulations=500, seed=7)
    assert "p_value_sharpe" in out
    assert out["n_trades"] == 6
    assert 0.0 <= out["p_value_sharpe"] <= 1.0


def test_gbm_paths_var_cvar() -> None:
    out = simulate_gbm_paths(s0=100_000.0, mu=0.1, sigma=0.25, horizon_days=252, n_paths=2000, seed=1)
    assert out["var_95"] < 0
    assert out["cvar_95"] <= out["var_95"]
    assert out["terminal_p50"] > 0


@pytest.fixture
def hyper_svc(tmp_path: Path) -> HyperSimulatorService:
    store = tmp_path / "runs.jsonl"
    facade = MagicMock()
    facade.run_backtest.return_value = (
        {
            "ok": True,
            "trades": [
                {"pnl": 500.0},
                {"pnl": -120.0},
                {"pnl": 300.0},
                {"pnl": 80.0},
            ],
            "metrics": {"sharpe_ratio": 1.2, "max_drawdown": -0.08},
        },
        "mock backtest",
    )
    return HyperSimulatorService(
        strategy_service=None,
        tool_facade_service=facade,
        simulation_gateway_service=None,
        store_path=store,
    )


def test_hyper_sim_combined_mode(hyper_svc: HyperSimulatorService) -> None:
    req = HyperSimRunRequest(
        symbol="600519",
        market="CN",
        mode="combined",
        n_simulations=300,
        horizon_days=60,
        strategy_name="trend_following",
    )
    out = hyper_svc.run(99, req)
    assert out["ok"] is True
    assert out["backtest"]["ok"] is True
    assert out["monte_carlo"]["n_trades"] == 4
    assert out["price_paths"]["n_paths"] == 300
    assert out["confidence"] > 0.5
    assert out["evidence"]


def test_hyper_sim_manifest() -> None:
    svc = HyperSimulatorService()
    manifest = svc.get_manifest()
    assert manifest["ok"] is True
    assert len(manifest["modes"]) == 3
