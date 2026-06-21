"""Dual-theme page smoke — structural checks for UI/CSS migration DoD.

Verifies four critical paths render with expected shell, page CSS links,
and no forbidden inline ``<style>`` blocks. CSS token files must define
both light and dark themes.

Full visual contrast/mobile checks remain manual; see
``docs/UI_CSS_THEME_VERIFICATION.md``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import werkzeug

ROOT = Path(__file__).resolve().parents[2]


def _seed_test_users(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "admin": {
            "id": 1,
            "password": hashlib.sha256(b"admin123").hexdigest(),
            "role": "admin",
            "wechat_openid": None,
            "display_name": "Admin",
            "avatar_url": None,
        }
    }
    (config_dir / "users.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    monkeypatch.setenv("ENABLE_BASIC_DATA_SCHEDULER", "0")
    monkeypatch.setenv("ENABLE_CELERY", "0")
    monkeypatch.setenv("ENABLE_QLIB", "0")
    monkeypatch.setenv("ENABLE_RD_AGENT", "0")
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "memory://")
    monkeypatch.setenv("SKIP_SECRETS_CHECKS", "1")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)
    instance = tmp_path / "instance"
    instance.mkdir()
    monkeypatch.setattr("app.config.settings.INSTANCE_DIR", instance)
    config_dir = tmp_path / "config"
    _seed_test_users(config_dir)
    monkeypatch.setattr("app.config.settings.CONFIG_DIR", config_dir)
    monkeypatch.setattr("app.config.CONFIG_DIR", config_dir)

    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303), login.get_data(as_text=True)[:500]
    return client


THEME_ROUTE_SPECS: tuple[dict[str, object], ...] = (
    {
        "name": "navigation_shell",
        "path": "/",
        "page_css": "css/pages/workbench.css",
        "markers": (
            b'class="app-shell"',
            b'id="themeToggle"',
            b"design-tokens.css",
            b"common.css",
            b"base_app.js",
            b"localStorage.getItem('theme')",
            b"wb-hero",
            b"nav-links",
        ),
    },
    {
        "name": "daily_workbench",
        "path": "/",
        "page_css": "css/pages/workbench.css",
        "markers": (
            b"wbFocusBar",
            b"btn-brand",
        ),
    },
    {
        "name": "stock_detail",
        "path": "/stock/600519",
        "page_css": "css/pages/stock-detail.css",
        "markers": (
            b"stock-detail-hero",
            b"section-shell",
            b"resonance-meter",
            b"evidence-card.css",
        ),
    },
    {
        "name": "backtest",
        "path": "/backtest",
        "page_css": "css/pages/strategy.css",
        "markers": (
            b"bt-form-panel",
            b"score-card",
            b"section-shell",
        ),
    },
)


@pytest.mark.parametrize("spec", THEME_ROUTE_SPECS, ids=[str(s["name"]) for s in THEME_ROUTE_SPECS])
def test_theme_route_renders_with_page_css(app_client, spec: dict[str, object]) -> None:
    path = str(spec["path"])
    resp = app_client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
    body = resp.data
    body_lower = body.lower()
    assert b"<style" not in body_lower, f"{path} must not contain inline <style>"
    page_css = str(spec["page_css"]).encode()
    assert page_css in body, f"{path} missing link to {spec['page_css']}"
    for marker in spec["markers"]:  # type: ignore[union-attr]
        assert marker in body, f"{path} missing marker {marker!r}"


def test_login_uses_auth_css_without_inline_style(app_client) -> None:
    resp = app_client.get("/login")
    assert resp.status_code == 200
    body = resp.data
    assert b"css/pages/auth.css" in body
    assert b"login-shell" in body
    assert b"<style" not in body.lower()


def test_design_tokens_define_light_and_dark() -> None:
    tokens = (ROOT / "static/css/design-tokens.css").read_text(encoding="utf-8")
    assert '[data-theme="dark"]' in tokens or ":root" in tokens
    assert '[data-theme="light"]' in tokens


def test_common_css_has_theme_overrides() -> None:
    common = (ROOT / "static/css/common.css").read_text(encoding="utf-8")
    assert common.count('[data-theme="light"]') >= 3
    assert common.count('[data-theme="dark"]') >= 3


@pytest.mark.parametrize(
    "css_rel",
    [
        "static/css/pages/workbench.css",
        "static/css/pages/stock-detail.css",
        "static/css/pages/strategy.css",
        "static/css/pages/auth.css",
    ],
)
def test_page_css_files_exist_and_use_tokens(css_rel: str) -> None:
    path = ROOT / css_rel
    assert path.is_file(), f"missing {css_rel}"
    text = path.read_text(encoding="utf-8")
    assert "var(--" in text, f"{css_rel} should reference design tokens"


def test_static_page_css_served(app_client) -> None:
    for css in (
        "/static/css/design-tokens.css",
        "/static/css/common.css",
        "/static/css/pages/workbench.css",
        "/static/css/pages/stock-detail.css",
        "/static/css/pages/strategy.css",
    ):
        resp = app_client.get(css)
        assert resp.status_code == 200, css
        assert resp.content_type and "css" in resp.content_type
