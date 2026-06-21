"""Phase 30: Celery worker DB cleanup + task_wiring lazy repository imports."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_task_wiring_does_not_import_repository_deps_at_module_level() -> None:
    imports = _top_level_imports(ROOT / "app" / "tasks" / "task_wiring.py")
    assert "app.infrastructure.repositories.deps" not in imports
    assert "app.infrastructure.repositories.common.deps" not in imports


def test_cleanup_worker_db_resources_closes_mysql_and_scoped_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks.worker_db_cleanup import cleanup_worker_db_resources

    mysql_close = MagicMock()
    scoped_cleanup = MagicMock()
    monkeypatch.setattr(
        "app.infrastructure.database.mysql_client.mysql_close_thread_local_connection",
        mysql_close,
    )
    monkeypatch.setattr(
        "app.tasks.task_wiring.cleanup_worker_scoped_session",
        scoped_cleanup,
    )

    cleanup_worker_db_resources()
    mysql_close.assert_called_once()
    scoped_cleanup.assert_called_once()


def test_cleanup_worker_scoped_session_is_noop_without_factory() -> None:
    import app.tasks.task_wiring as wiring

    wiring._worker_session_factory = None
    wiring.cleanup_worker_scoped_session()


def test_cleanup_worker_scoped_session_calls_remove() -> None:
    import app.tasks.task_wiring as wiring

    factory = MagicMock()
    wiring._worker_session_factory = factory
    wiring.cleanup_worker_scoped_session()
    factory.remove.assert_called_once()
    wiring._worker_session_factory = None


def test_create_basic_market_data_repository_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import task_wiring

    repo = object()
    factory = MagicMock(return_value=repo)
    monkeypatch.setattr(
        "app.infrastructure.repositories.common.deps.create_basic_market_data_repository",
        factory,
    )
    settings = MagicMock()
    assert task_wiring._create_basic_market_data_repository(settings) is repo
    factory.assert_called_once_with(settings)
