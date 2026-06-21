"""Phase B — navigation IA and api_client contract checks."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_HTML = ROOT / "app" / "presentation" / "web" / "templates" / "base.html"
API_CLIENT = ROOT / "static" / "js" / "api_client.js"
TRUTH_CLIENT = ROOT / "static" / "js" / "truth_badge_client.js"


def test_base_nav_four_top_level_menus():
    text = BASE_HTML.read_text(encoding="utf-8")
    for label in ("🏠 操盘台", "🔬 研究", "📈 策略", "👤 我的"):
        assert label in text
    # Legacy top-level menus removed from primary nav
    assert 'id="navDdMarket"' not in text
    assert 'id="navDdAi"' not in text
    assert 'id="navDdSystem"' not in text


def test_retail_assistant_is_primary_mine_entry():
    text = BASE_HTML.read_text(encoding="utf-8")
    assert 'href="/retail-assistant"' in text
    assert 'href="/user-tiers/retail"' not in text


def test_strategy_wizard_and_data_lake_in_nav():
    text = BASE_HTML.read_text(encoding="utf-8")
    assert 'href="/strategy-wizard"' in text
    assert 'href="/data-lake-health"' in text


def test_api_client_exports_unwrap():
    text = API_CLIENT.read_text(encoding="utf-8")
    assert "function unwrap" in text
    assert "unwrap: unwrap" in text
    assert "QCApi" in text


def test_truth_badge_client_uses_qcapi_path():
    text = TRUTH_CLIENT.read_text(encoding="utf-8")
    assert "QCTruthBadge" in text
    assert "/truth/badge/" in text
