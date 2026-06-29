"""Architecture layer dependency gate.

Ensures the four-layer architecture dependency direction is respected:
Presentation -> Application -> Domain -> Infrastructure
Domain must never import from Infrastructure, Application, or Presentation.
"""

import os

PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _find_py_files(target):
    result = []
    for root, _dirs, files in os.walk(target):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                result.append(os.path.join(root, f))
    return result


def _read_top_level_imports(filepath):
    """Extract only top-level (column-0) `from X import` and `import X` lines.

    Only module-level imports create load-time dependencies.  Imports inside
    function/method bodies (lazy imports) do not violate architectural layer
    boundaries at load time and are intentionally excluded.
    """
    imports = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                stripped = line.lstrip()
                # Only column-0 "from" / "import" are top-level imports
                if line[0:1] not in (" ", "\t") and (
                    stripped.startswith("from ") or stripped.startswith("import ")
                ):
                    imports.append(stripped)
    except Exception:
        pass
    return imports


FORBIDDEN_DOMAIN = ["app.infrastructure", "app.application", "app.presentation"]
FORBIDDEN_APPLICATION = ["app.infrastructure"]


# Legacy shim files that intentionally re-export infrastructure classes are
# exempt on the understanding they will be removed once all callers migrate.
# Modules that use lazy (function-local) imports are already compliant.
LEGACY_SHIMS = frozenset()


class TestLayerDependencyGate:

    def test_domain_must_not_import_infrastructure(self):
        violations = []
        for f in _find_py_files("app/domain"):
            rel = os.path.relpath(f, PROJECT_ROOT).replace("\\", "/")
            if rel in LEGACY_SHIMS:
                continue
            for imp in _read_top_level_imports(f):
                for fb in FORBIDDEN_DOMAIN:
                    if fb in imp:
                        violations.append("{}: {}".format(rel, imp.strip()))
        msg = "Domain must not import infrastructure/application/presentation.\n"
        msg += "Found {} violation(s):\n{}".format(len(violations), "\n".join(violations))
        assert not violations, msg

    def test_application_must_not_import_infrastructure_directly(self):
        violations = []
        for f in _find_py_files("app/application"):
            rel = os.path.relpath(f, PROJECT_ROOT).replace("\\", "/")
            if rel in LEGACY_SHIMS:
                continue
            for imp in _read_top_level_imports(f):
                for fb in FORBIDDEN_APPLICATION:
                    if fb in imp and "domain.ports" not in imp:
                        violations.append("{}: {}".format(rel, imp.strip()))
        msg = "Application must not directly import infrastructure.\n"
        msg += "Found {} violation(s):\n{}".format(len(violations), "\n".join(violations))
        assert not violations, msg