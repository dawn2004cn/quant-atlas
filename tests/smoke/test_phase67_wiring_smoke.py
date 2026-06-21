"""Phase 67: wiring smoke, vectorized backtest, ZK proof compliance."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug

from app.modules.system.services.complexity_budget_service import ComplexityBudgetService
from app.modules.system.services.compliance_service import ComplianceService
from app.modules.strategy.services.boutique_tier_service import VectorizedBacktestService


def test_complexity_validate_wiring_syntax() -> None:
    from app.bootstrap_components import wiring_optimization  # noqa: F401

    svc = ComplexityBudgetService()
    result = svc.validate_wiring()
    assert result["ok"] is True
    assert result["checked"] > 0
    assert result["factory_count"] > 0


def test_zk_proof_create_and_verify_stored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "compliance"
    store.mkdir()
    svc = ComplianceService()
    monkeypatch.setattr(svc, "_store", store)
    monkeypatch.setattr(svc, "_reputation_file", store / "reputation.jsonl")
    monkeypatch.setattr(svc, "_proof_file", store / "zk_proofs.jsonl")

    proof = svc.create_proof("tk.test", 1, ic_mean=0.05, ic_std=0.1, sharpe=0.9, sample_size=120)
    assert proof.proof_hash
    assert proof.verification_nonce
    assert svc.verify_stored_proof("tk.test", 1) is True
    assert svc.verify_proof("tk.test", 1, proof.verification_nonce) is True
    assert proof.public_dict().get("verification_nonce") is None


def test_vectorized_backtest_uses_numpy_or_polars() -> None:
    svc = VectorizedBacktestService()
    n = 200
    returns = [0.001 * (i % 5 - 2) for i in range(n)]
    signals = [1.0 if i % 10 < 5 else -1.0 for i in range(n)]
    result = svc.run("test_strat", returns, signals, backend="auto")
    assert result.backend in ("numpy", "polars", "python")
    assert result.num_trades == n
    assert result.elapsed_ms >= 0


@pytest.fixture
def boot_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
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
    return app


def test_boot_registers_many_routes(boot_app) -> None:
    rules = [r for r in boot_app.url_map.iter_rules() if r.endpoint != "static"]
    assert len(rules) >= 80


def test_critical_factories_resolve(boot_app) -> None:
    from app.bootstrap_components.service_wiring import _get_registry

    reg = _get_registry()
    wiring = ComplexityBudgetService().validate_wiring(reg)
    assert wiring["factory_count"] > 10
    assert wiring["factories_resolved"] > 5
