from __future__ import annotations

from pathlib import Path

from app.modules.user.services.user.page_preference_service import PagePreferenceService


def test_stock_detail_layout_persisted(tmp_path: Path) -> None:
    svc = PagePreferenceService(store_path=tmp_path / "prefs.json")
    updated = svc.update_preferences(
        "u1",
        {"stock_detail_layout": ["resonance-meter", "decision-brief-strip", "invalid-id"]},
    )
    assert "resonance-meter" in updated["stock_detail_layout"]
    assert "invalid-id" not in updated["stock_detail_layout"]
    loaded = svc.get_preferences("u1")
    assert loaded["stock_detail_layout"][0] == "resonance-meter"
