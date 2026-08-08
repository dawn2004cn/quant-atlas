"""Phase E3.1 acceptance — presentation route modules stay under size budget."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "app" / "presentation" / "api"
MAX_ROUTE_FILE_LINES = 800

ROUTE_GLOBS = (
    "routes_v1_*.py",
    "routes_v2*.py",
    "v1/**/*.py",
)


def _route_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ROUTE_GLOBS:
        files.extend(API_ROOT.glob(pattern))
    return sorted({p for p in files if p.is_file()})


def test_no_presentation_route_file_exceeds_line_budget():
    oversize: list[tuple[int, str]] = []
    for path in _route_files():
        line_count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
        if line_count > MAX_ROUTE_FILE_LINES:
            oversize.append((line_count, str(path.relative_to(ROOT))))
    assert not oversize, "oversized route files:\n" + "\n".join(
        f"{n} lines  {p}" for n, p in sorted(oversize, reverse=True)
    )
