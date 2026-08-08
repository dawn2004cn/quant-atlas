"""Phase E4.3 — Celery tasks must not depend on the presentation layer."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS_ROOT = ROOT / "app" / "tasks"

FORBIDDEN_TASK_IMPORT_MARKERS = (
    "app.presentation",
    "presentation.api",
    "presentation.web",
    "flask",
)


def _iter_task_py_files() -> list[Path]:
    return sorted(p for p in TASKS_ROOT.rglob("*.py") if p.is_file())


def _collect_import_markers(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for marker in FORBIDDEN_TASK_IMPORT_MARKERS:
                    if marker in alias.name:
                        hits.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for marker in FORBIDDEN_TASK_IMPORT_MARKERS:
                if marker in module:
                    hits.append(f"from {module} import ...")
    return hits


def test_tasks_do_not_import_presentation_or_flask():
    violations: list[str] = []
    for path in _iter_task_py_files():
        rel = path.relative_to(ROOT)
        for hit in _collect_import_markers(path):
            violations.append(f"{rel}: {hit}")
    assert not violations, "tasks layer presentation/flask imports:\n" + "\n".join(violations[:20])


def test_task_registry_populated_with_app_tasks_prefix():
    from app.tasks.registry import ensure_task_registry

    registry = ensure_task_registry()
    assert len(registry) >= 15
    bad = [name for name in registry if not name.startswith("app.tasks.")]
    assert not bad, f"task registry keys must use app.tasks.* prefix: {bad[:10]}"


def test_task_registry_entries_expose_callable():
    from app.tasks.registry import ensure_task_registry

    registry = ensure_task_registry()
    for name, info in registry.items():
        func = info.get("func")
        assert callable(func), f"{name} missing callable func"


def test_celery_task_dispatcher_implements_port():
    from app.domain.ports.task_ports import TaskDispatcher
    from app.infrastructure.messaging.task_dispatcher import CeleryTaskDispatcher

    dispatcher = CeleryTaskDispatcher()
    assert isinstance(dispatcher, TaskDispatcher)
    assert callable(dispatcher.dispatch)
    assert callable(dispatcher.get_task_label)
