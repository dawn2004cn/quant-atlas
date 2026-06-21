"""Phase 29: memory / monitoring / metrics presentation cleanup."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.system.services.helpers.metrics_access import (
    bind_metrics_infrastructure,
    build_metrics_summary,
    prometheus_metrics_content_type,
    render_prometheus_metrics,
)
from app.modules.system.services.helpers.monitoring_access import (
    bind_monitoring_infrastructure,
    check_table_freshness,
)
from app.modules.system.services.system.memory_optimization_service import MemoryOptimizationService

ROOT = Path(__file__).resolve().parents[1]


def _collect_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_memory_routes_do_not_import_arrow_pool() -> None:
    imports = _collect_imports(ROOT / "app" / "presentation" / "api" / "routes_v1_memory.py")
    assert "app.infrastructure.memory.arrow_pool" not in imports


def test_monitoring_routes_do_not_import_sentinel() -> None:
    imports = _collect_imports(ROOT / "app" / "presentation" / "api" / "routes_v1_monitoring.py")
    assert "app.infrastructure.monitoring.sentinel" not in imports


def test_metrics_routes_do_not_import_prometheus_impl() -> None:
    imports = _collect_imports(ROOT / "app" / "presentation" / "api" / "routes_metrics.py")
    assert "app.infrastructure.metrics" not in imports


def test_memory_optimization_service_list_tables() -> None:
    manager = MagicMock()
    pool = MagicMock()
    pool.list_tables.return_value = ["quotes", "bars"]
    manager.get_pool.return_value = pool
    service = MemoryOptimizationService(manager=manager)

    assert service.list_tables("research") == ["quotes", "bars"]
    manager.get_pool.assert_any_call("research")


def test_monitoring_access_uses_bound_checker() -> None:
    checker = MagicMock(return_value=True)
    bind_monitoring_infrastructure(check_table_freshness=checker)

    assert check_table_freshness("stock_history_sh", max_delay_minutes=30) is True
    checker.assert_called_once_with("stock_history_sh", 30)


def test_metrics_access_uses_bound_helpers() -> None:
    bind_metrics_infrastructure(
        get_metrics=lambda: b"metric 1",
        get_metrics_content_type=lambda: "text/plain; version=0.0.4",
        get_metrics_summary=lambda: {"running_tasks": 2, "active_users": 5},
    )

    assert render_prometheus_metrics() == b"metric 1"
    assert prometheus_metrics_content_type().startswith("text/plain")
    assert build_metrics_summary()["running_tasks"] == 2
