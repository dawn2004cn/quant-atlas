"""Celery task layer boundary tests (phase 9)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_ROOT = ROOT / "app" / "tasks"
# Single wiring hub may import infrastructure; other task modules must not.
TASK_WIRING_EXEMPT = TASKS_ROOT / "task_wiring.py"

# Phase 9a: domain symbols + ingestor wiring; 9b: providers via task_wiring.
FORBIDDEN_IMPORT_MARKERS = (
    "infrastructure.mappers.symbol_normalizer",
    "infrastructure.qlib.symbol_map",
    "infrastructure.adapters.market_ingestion.longhu_adapter",
    "infrastructure.providers",
    "infrastructure.database",
    "infrastructure.messaging",
    "infrastructure.rdagent",
    "infrastructure.adapters",
    "infrastructure.tracing",
)

REPOSITORY_FORBIDDEN_PREFIX = "infrastructure.repositories"
REPOSITORY_ALLOWED = "infrastructure.repositories.deps"


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _read_source(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if b"\x00" in raw[:200]:
        return raw.decode("utf-16-le")
    return raw.decode("utf-8")


def _is_forbidden_module(module: str) -> bool:
    for marker in FORBIDDEN_IMPORT_MARKERS:
        if marker in module:
            return True
    if REPOSITORY_FORBIDDEN_PREFIX in module and REPOSITORY_ALLOWED not in module:
        return True
    return False


def _collect_import_violations(path: Path) -> list[str]:
    source = _read_source(path)
    tree = ast.parse(source, filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_module(alias.name):
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_forbidden_module(module):
                violations.append(f"from {module} import ...")
    return violations


def test_tasks_avoid_direct_infra_for_bound_symbols_and_ingestor():
    offenders: list[str] = []
    for path in _iter_py_files(TASKS_ROOT):
        if path == TASK_WIRING_EXEMPT:
            continue
        for msg in _collect_import_violations(path):
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}: {msg}")
    assert not offenders, (
        "tasks layer should use task_wiring, deps, and application helpers:\n"
        + "\n".join(offenders)
    )
