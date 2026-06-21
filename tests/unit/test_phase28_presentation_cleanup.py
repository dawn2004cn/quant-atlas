"""Phase 28: legacy/task_ops/health presentation boundary cleanup."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.system.services.system.system_health_probe_service import SystemHealthProbeService

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


def test_legacy_routes_do_not_import_market_data_provider() -> None:
    imports = _collect_imports(ROOT / "app" / "presentation" / "api" / "legacy_routes.py")
    assert "app.infrastructure.providers.market_data" not in imports
    assert "app.core.utils.datetime_utils" in imports


def test_task_ops_routes_do_not_import_celery_admin_adapter() -> None:
    imports = _collect_imports(ROOT / "app" / "presentation" / "api" / "routes_v1_task_ops.py")
    assert "app.infrastructure.adapters.celery_task_admin" not in imports


def test_task_ops_access_uses_bound_callables() -> None:
    from app.modules.system.services.helpers.task_ops_access import (
        bind_task_ops_infrastructure,
        get_celery_task_status,
        inspect_celery_snapshot,
        revoke_celery_task,
    )

    inspect_mock = MagicMock(return_value={"ok": True})
    status_mock = MagicMock(return_value={"state": "SUCCESS"})
    revoke_mock = MagicMock(return_value={"ok": True})
    bind_task_ops_infrastructure(
        inspect_snapshot=inspect_mock,
        task_status=status_mock,
        revoke_task=revoke_mock,
    )

    assert inspect_celery_snapshot(timeout=1.0) == {"ok": True}
    inspect_mock.assert_called_once_with(timeout=1.0)
    assert get_celery_task_status("task-1") == {"state": "SUCCESS"}
    status_mock.assert_called_once_with("task-1")
    assert revoke_celery_task("task-2", terminate=True) == {"ok": True}
    revoke_mock.assert_called_once_with("task-2", terminate=True)


def test_system_health_probe_async_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    queue = MagicMock()
    queue._max_workers = 4
    monkeypatch.setattr(
        "app.infrastructure.task_queue.get_task_queue",
        lambda: queue,
    )
    result = SystemHealthProbeService.probe_async_queue()
    assert result == {"status": "ok", "workers": 4}
