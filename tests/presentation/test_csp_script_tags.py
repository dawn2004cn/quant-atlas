"""Regression: inline script tags must close with '>' after CSP nonce patch."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "presentation" / "web" / "templates"
BROKEN = re.compile(
    r'<script([^>]*\bnonce\s*=\s*"\{\{\s*csp_nonce\(\)\s*\}\}")(?!\s*>)',
    re.IGNORECASE,
)


@pytest.mark.parametrize("path", sorted(TEMPLATES.rglob("*.html")), ids=lambda p: p.name)
def test_inline_script_nonce_tag_is_closed(path: Path) -> None:
    offenders = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if BROKEN.search(line):
            offenders.append(f"{path.relative_to(TEMPLATES)}:{lineno}")
    assert not offenders, "broken <script> tags:\n" + "\n".join(offenders)
