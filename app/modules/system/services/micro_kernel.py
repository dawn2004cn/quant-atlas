"""Micro-Kernel standard — Phase 16. Enforce wiring_*.py factory pattern across modules."""

from __future__ import annotations

import ast
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


class ModuleKernelValidator:
    """Validates all modules follow the Micro-Kernel pattern:
    Domain (pure logic) → Application (orchestration) → Adapter (external)
    No direct service-import; all via Registry.
    """

    FORBIDDEN_PATTERNS = [
        "from app.application.services",
        "from app.modules.",
    ]

    def __init__(self):
        self._modules_root = Path(__file__).resolve().parents[4] / "modules"

    def validate_module(self, module_name: str) -> list[str]:
        """Check a module for forbidden import patterns."""
        violations = []
        module_dir = self._modules_root / module_name
        if not module_dir.exists():
            return [f"Module {module_name} not found"]

        for py_file in module_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            try:
                tree = ast.parse(py_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        full_path = f"{node.module or ''}"
                        for pattern in self.FORBIDDEN_PATTERNS:
                            if pattern in full_path:
                                violations.append(
                                    f"{py_file.relative_to(self._modules_root)}: "
                                    f"forbidden import '{full_path}' (use Registry instead)"
                                )
            except SyntaxError:
                violations.append(f"{py_file.name}: syntax error")

        return violations

    def audit_all_modules(self) -> dict[str, list[str]]:
        """Audit all modules for Micro-Kernel violations."""
        results = {}
        for d in self._modules_root.iterdir():
            if d.is_dir() and not d.name.startswith("_"):
                violations = self.validate_module(d.name)
                if violations:
                    results[d.name] = violations
        return results
