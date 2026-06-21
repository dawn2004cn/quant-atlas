"""Lightweight secrets scan — blocks known bad defaults in app/."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"

BANNED_LITERALS = (
    "changeme",
    "AdminPassword123!",
    "root123",
    "redis://192.168.",
)


@pytest.mark.parametrize("needle", BANNED_LITERALS)
def test_no_banned_secrets_in_app(needle: str):
    hits: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        if "test_" in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if needle in text:
            hits.append(str(path.relative_to(ROOT)))
    assert not hits, f"Found banned literal {needle!r} in: {hits}"
