"""Phase 27: factor lifecycle Celery sync runners + health route registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.presentation.api.routes import create_api_blueprint


def test_factor_lifecycle_tasks_import_without_syntax_error() -> None:
    from app.tasks import factor_lifecycle_tasks as mod

    assert callable(mod.run_factor_lifecycle_daily_check)
    assert callable(mod.run_factor_ic_calculation)
    assert callable(mod.run_factor_cleanup_archived)


def test_run_factor_lifecycle_daily_check_skips_without_mysql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks.factor_lifecycle_tasks import run_factor_lifecycle_daily_check

    settings = MagicMock()
    settings.use_mysql = False
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    result = run_factor_lifecycle_daily_check()
    assert result == {"status": "skipped", "reason": "MySQL not enabled"}


def test_run_factor_ic_calculation_processes_active_factors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks.factor_lifecycle_tasks import run_factor_ic_calculation

    settings = MagicMock()
    settings.use_mysql = True
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    repo = MagicMock()
    repo.get_factor = AsyncMock(return_value=None)
    repo.list_factors = AsyncMock(
        return_value=[{"factor_id": "factor_a"}, {"factor_id": "factor_b"}]
    )
    repo.get_ic_history = AsyncMock(
        side_effect=[
            [{"ic_value": 0.1}] * 10,
            [{"ic_value": 0.2}] * 10,
        ]
    )

    service = MagicMock()
    service.update_factor_performance = AsyncMock(
        side_effect=[
            {"ic_mean": 0.1, "ir": 0.5},
            {"ic_mean": 0.2, "ir": 0.6},
        ]
    )

    monkeypatch.setattr(
        "app.infrastructure.repositories.common.deps.create_factor_repository",
        lambda _settings: repo,
    )
    monkeypatch.setattr(
        "app.domain.factor_service.FactorService",
        lambda _repo: service,
    )

    result = run_factor_ic_calculation()
    assert result["status"] == "completed"
    assert result["factors_processed"] == 2
    assert service.update_factor_performance.await_count == 2


def test_health_routes_registered_on_api_blueprint() -> None:
    from flask import Flask

    bundle = MagicMock()
    blueprint = create_api_blueprint(
        bundle,
        task_dispatcher=MagicMock(),
        task_message_store=MagicMock(),
    )
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/system/health" in rules
    assert "/api/v1/system/events" in rules
    assert "/api/v1/system/test-event" in rules
    assert "/api/v1/market/sentiment/diary" in rules
    assert "/api/v1/ai-hedge-fund/analyze" in rules
