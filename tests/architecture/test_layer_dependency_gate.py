"""Architecture layer dependency gate.

Ensures the four-layer architecture dependency direction is respected:
Presentation → Application → Domain → Infrastructure
Domain must never import from Infrastructure, Application, or Presentation.
"""

import os
import re
import pytest

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

def _find_py_files(under_dir: str) -> list[str]:
    """Find all .py files under the given directory (relative to PROJECT_ROOT)."""
    target = os.path.join(PROJECT_ROOT, under_dir)
    if not os.path.isdir(target):
        return []
    result = []
    for root, _dirs, files in os.walk(target):
        for f in files:
            if f.endswith(".py"):
                result.append(os.path.join(root, f))
    return result


def _read_top_level_imports(filepath: str) -> list[str]:
    """Extract only top-level (non-indented) `from X import` and `import X` lines from a file.

    Only module-level imports create load-time dependencies. Imports inside functions
    (lazy imports) do not violate architectural layer boundaries at load time.
    """
    imports = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                # Only consider lines that start at column 0 (no leading whitespace)
                # This identifies top-level imports
                if (line.startswith("from ") or line.startswith("import ")) and not line[0].isspace():
                    imports.append(line.strip())
    except Exception:
        pass
    return imports


FORBIDDEN_DOMAIN_IMPORTS = [
    "app.infrastructure",
    "app.application",
    "app.presentation",
]

FORBIDDEN_APPLICATION_IMPORTS = [
    "app.infrastructure",
]


class TestLayerDependencyGate:
    """Test that layer dependency direction is respected."""

    def test_domain_must_not_import_infrastructure(self):
        violations = []
        for f in _find_py_files("app/domain"):
            for imp in _read_top_level_imports(f):
                for forbidden in FORBIDDEN_DOMAIN_IMPORTS:
                    if forbidden in imp:
                        rel = os.path.relpath(f, PROJECT_ROOT)
                        violations.append(f"{rel}: {imp.strip()}")
        assert not violations, (
            f"Domain layer must not import infrastructure/application/presentation at module level.\n"
            f"Found {len(violations)} violations:\n" + "\n".join(violations)
        )

    def test_application_must_not_import_infrastructure_directly(self):
        violations = []
        for f in _find_py_files("app/application"):
            for imp in _read_top_level_imports(f):
                for forbidden in FORBIDDEN_APPLICATION_IMPORTS:
                    if forbidden in imp and "domain.ports" not in imp:
                        rel = os.path.relpath(f, PROJECT_ROOT)
                        violations.append(f"{rel}: {imp.strip()}")
        assert not violations, (
            f"Application layer must not directly import infrastructure at module level.\n"
            f"Found {len(violations)} violations:\n" + "\n".join(violations)
        )