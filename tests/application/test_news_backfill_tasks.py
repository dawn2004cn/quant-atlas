"""新闻归档批量任务（无网络）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.enums import MarketCode
from app.tasks import news_backfill_tasks as nbt


def test_run_news_archive_force_refresh_uses_mock_access(monkeypatch) -> None:
    mock_access = MagicMock()
    mock_access.fetch_bundled.return_value = {
        "news": [],
        "industry_news": [],
        "archive_total_rows": 5,
        "remote_refreshed": True,
    }
    monkeypatch.setattr(nbt, "_stock_news_access", lambda: mock_access)
    monkeypatch.setattr(nbt.time, "sleep", lambda _s: None)
    r = nbt.run_news_archive_force_refresh_for_codes(["600519"], sleep_sec=0.0, max_codes=10)
    assert r.get("ok") is True
    assert r.get("codes_total") == 1
    mock_access.fetch_bundled.assert_called_once()
    ca = mock_access.fetch_bundled.call_args
    assert ca[0][0] == "600519"
    assert ca[0][1] == MarketCode.CN
    assert ca[1].get("force_refresh") is True

