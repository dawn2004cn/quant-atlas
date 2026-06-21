"""Tests verifying presentation layer has no module-level infrastructure imports."""

from __future__ import annotations

import ast
from pathlib import Path

# All Python files under app/presentation (recursive)
PRESENTATION_DIR = Path(__file__).resolve().parent.parent / "app" / "presentation"


def _get_project_root() -> Path:
    """Return project root (grandparent of tests/unit/domain/)."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_python_files() -> list[Path]:
    return sorted((_get_project_root() / "app" / "presentation").rglob("*.py"))


def _has_module_level_infra_import(source: str) -> list[str]:
    """Return list of module-level infrastructure imports found."""
    tree = ast.parse(source)
    violations = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app.infrastructure"):
                names = ", ".join(a.name for a in node.names)
                violations.append(f"from {node.module} import {names}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.infrastructure"):
                    violations.append(f"import {alias.name}")
    return violations


class TestPresentationDIP:
    """Verify presentation layer doesn't have module-level infrastructure imports."""

    def test_no_module_level_infrastructure_imports(self):
        """No .py file in presentation/ should have module-level infra imports."""
        violations_by_file: dict[str, list[str]] = {}

        for pyfile in _get_python_files():
            source = pyfile.read_text(encoding="utf-8")
            v = _has_module_level_infra_import(source)
            if v:
                # Relative path from presentation dir
                rel = str(pyfile.relative_to(PRESENTATION_DIR))
                violations_by_file[rel] = v

        assert violations_by_file == {}, (
            f"Found module-level infrastructure imports in presentation layer:\n"
            + "\n".join(f"  {f}: {v}" for f, vs in violations_by_file.items() for v in vs)
        )

    def test_local_infra_imports_are_ok(self):
        """Local (function-body) infrastructure imports are acceptable in presentation."""
        # The file routes_v1_stock.py has a local try/except import
        # which is a valid pattern for optional infrastructure dependencies.
        stock_route = _get_project_root() / "app" / "presentation" / "api" / "routes_v1_stock.py"
        source = stock_route.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Check that rust_indicators import is inside a function (local)
        has_local = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module:
                        if "rust_indicators" in child.module:
                            has_local = True

        assert has_local, "Expected rust_indicators import to be local inside a function"
