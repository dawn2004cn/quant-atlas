"""龙虎榜：空库跳过 vs 强制全量（无网络）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.application.services.basic_market_data_service import BasicMarketDataService


def test_run_longhu_full_historical_if_no_stock_skips_when_rows_exist() -> None:
    svc = BasicMarketDataService.__new__(BasicMarketDataService)
    repo = MagicMock()
    repo.count_longhu_rows.return_value = 3
    svc._repo = repo
    svc.ingest_longhu_em_between = MagicMock()
    r = BasicMarketDataService.run_longhu_full_historical_if_no_stock(svc, years=1, chunk_days=400, sleep_sec=0)
    assert r.get("skipped") is True
    assert r.get("reason") == "existing_longhu_data"
    svc.ingest_longhu_em_between.assert_not_called()


def test_run_longhu_full_historical_force_runs_when_rows_exist() -> None:
    svc = BasicMarketDataService.__new__(BasicMarketDataService)
    repo = MagicMock()
    repo.count_longhu_rows.return_value = 99
    svc._repo = repo
    svc.ingest_longhu_em_between = MagicMock(return_value={"ok": True, "rows": 2})
    r = BasicMarketDataService.run_longhu_full_historical_force(svc, years=1, chunk_days=400, sleep_sec=0)
    assert r.get("skipped") is False
    assert r.get("ok") is True
    assert svc.ingest_longhu_em_between.call_count >= 1
    repo.set_meta.assert_called()

