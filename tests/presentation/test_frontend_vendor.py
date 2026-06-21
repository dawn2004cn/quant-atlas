"""Pinned frontend vendor assets (jQuery / Bootstrap 4)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_jquery_and_bootstrap_vendor_files_exist():
    jquery = ROOT / "static/js/vendor/jquery-3.7.1.min.js"
    bootstrap_js = ROOT / "static/js/vendor/bootstrap-4.6.2.bundle.min.js"
    bootstrap_css = ROOT / "static/css/vendor/bootstrap-4.6.2.min.css"
    assert jquery.is_file() and jquery.stat().st_size > 10_000
    assert bootstrap_js.is_file() and bootstrap_js.stat().st_size > 10_000
    assert bootstrap_css.is_file() and bootstrap_css.stat().st_size > 10_000
    assert b"jQuery v3.7.1" in jquery.read_bytes()[:200]
    assert b"Bootstrap v4.6.2" in bootstrap_css.read_bytes()[:200]
