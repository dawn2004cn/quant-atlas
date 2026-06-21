"""Smoke test: app boots and critical P0 routes are registered.

Works without external MySQL/Redis by disabling heavy subsystems
via environment variables.
"""

from __future__ import annotations

import os

os.environ.setdefault("ENABLE_CELERY", "0")
os.environ.setdefault("ENABLE_QLIB", "0")
os.environ.setdefault("ENABLE_RD_AGENT", "0")
os.environ.setdefault("ENABLE_BACKGROUND_SCANNER", "0")
os.environ.setdefault("ENABLE_BASIC_DATA_SCHEDULER", "0")
os.environ.setdefault("MESH_ENABLED", "0")
os.environ.setdefault("PERCEPTION_ENABLED", "0")
os.environ.setdefault("TASK_MESSAGE_REDIS_URL", "memory://")
os.environ.setdefault("SKIP_SECRETS_CHECKS", "1")


def test_create_app_boots():
    from app import create_app
    app = create_app()
    assert app is not None


def test_core_routes_registered():
    from app import create_app
    app = create_app()
    rules = {r.rule for r in app.url_map.iter_rules()}

    assert "/api/v1/health" in rules
    assert "/api/v1/alpha-factory/status" in rules, "Missing alpha-factory/status"
    assert "/api/v1/alpha-factory/factors" in rules
    assert "/api/v1/alpha-factory/knowledge/alphas" in rules
    assert "/api/v1/alpha-factory/model/meta-learner" in rules
    assert "/api/v1/alpha-factory/validate" in rules
    assert "/api/v1/alpha-factory/correlation" in rules
    assert "/api/v1/alpha-factory/model-zoo" in rules
    assert "/api/v1/alpha-factory/paper-trading" in rules
    assert "/api/v1/alpha-factory/weekly" in rules
    assert "/api/v1/alpha-factory/pipeline" in rules
    assert "/api/v1/rd-agent/runs" in rules, "Missing rd-agent/runs"
    assert "/api/v1/signal-flag/pool" in rules, "Missing signal-flag/pool"
    assert "/api/v1/signal-flag/scan" in rules


def test_no_404_core_endpoints():
    from app import create_app
    app = create_app()
    client = app.test_client()

    resp = client.get("/api/v1/health")
    assert resp.status_code in (200, 401)

    resp = client.get("/api/v1/alpha-factory/status")
    assert resp.status_code in (200, 401, 302)

    resp = client.get("/api/v1/alpha-factory/knowledge/alphas")
    assert resp.status_code in (200, 401, 302)

    resp = client.get("/api/v1/signal-flag/pool?date=2025-01-01")
    assert resp.status_code in (200, 401, 302)


def test_endpoints_return_valid_json():
    from app import create_app
    app = create_app()
    client = app.test_client()

    endpoints = [
        "/api/v1/health",
    ]
    for path in endpoints:
        resp = client.get(path)
        if resp.status_code == 200:
            import json
            data = json.loads(resp.data)
            assert isinstance(data, dict), f"{path} should return JSON object"


def test_knowledge_alphas_data():
    from app.domain.alpha.worldquant_alphas import ALPHA_EXAMPLES, ALPHA_OPERATORS
    assert len(ALPHA_EXAMPLES) > 0
    assert len(ALPHA_OPERATORS) > 0


def test_signal_flag_service_import():
    from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
    assert SignalFlagScannerService is not None


def test_alpha_factory_orchestrator_import():
    from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator
    assert get_orchestrator is not None


def test_rd_agent_tasks_import():
    from app.tasks.rdagent_tasks import run_rdagent_factor_generation, celery_rdagent_enabled
    assert callable(run_rdagent_factor_generation)


def test_trade_plan_service_no_garbled():
    from app.modules.execution.services.trade_plan_service import TradePlanService
    import inspect
    src = inspect.getsource(TradePlanService)
    assert "??" not in src, "Trade plan service still has garbled ?? text"


def test_csrf_protection_import():
    from app.presentation.csrf_protection import csrf_protect, _validate_csrf_token
    assert callable(csrf_protect)