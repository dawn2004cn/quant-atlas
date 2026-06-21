"""Login form must include CSRF fields for POST /login."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGIN_TEMPLATE = ROOT / "app" / "presentation" / "web" / "templates" / "login.html"


def test_login_template_includes_csrf_markup() -> None:
    text = LOGIN_TEMPLATE.read_text(encoding="utf-8")
    assert "{{ csrf_html() }}" in text
    assert 'name="csrf-token"' in text
    assert "{{ csrf_token() }}" in text
