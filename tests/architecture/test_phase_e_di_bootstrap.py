"""Phase E — bootstrap / DI architecture gates."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"


def _iter_python_files() -> list[Path]:
    return [p for p in APP_ROOT.rglob("*.py") if p.is_file()]


def test_no_wildcard_import_from_bootstrap_services():
    """``create_services`` is the only supported import from services bootstrap."""
    forbidden = "from app.bootstrap_components.services import *"
    hits: list[str] = []
    for path in _iter_python_files():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if forbidden in text:
            hits.append(str(path.relative_to(ROOT)))
    assert not hits, f"wildcard bootstrap services import in: {hits}"


def test_bootstrap_services_shim_reexports_create_services():
    from app import bootstrap_services
    from app.bootstrap_components import services as canonical

    assert bootstrap_services.create_services is canonical.create_services


def test_post_wire_hooks_module_exports_runner():
    from app.bootstrap_components.post_wire_hooks import run_post_wire_hooks

    assert callable(run_post_wire_hooks)


def test_services_module_documents_single_entry_point():
    import app.bootstrap_components.services as mod

    doc = mod.__doc__ or ""
    assert "create_services" in doc
    assert "import *" in doc
