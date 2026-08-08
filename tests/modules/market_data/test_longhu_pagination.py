from __future__ import annotations

from app.infrastructure.repositories.sqlite.sqlite_basic_market_data_repository import (
    SQLiteBasicMarketDataRepository,
)


def test_longhu_by_date_pagination(tmp_path) -> None:
    repo = SQLiteBasicMarketDataRepository(db_path=str(tmp_path / "basic.db"))
    trade_date = "2026-07-28"
    rows = [
        {
            "trade_date": trade_date,
            "code": f"60000{i}",
            "name": f"股票{i}",
            "reason": "测试",
            "raw": {},
        }
        for i in range(5)
    ]
    repo.replace_longhu_day(trade_date, rows)

    page1 = repo.list_longhu_by_date(trade_date, limit=2, offset=0)
    page2 = repo.list_longhu_by_date(trade_date, limit=2, offset=2)
    total = repo.count_longhu_by_date(trade_date)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["code"] == "600000"
    assert page2[0]["code"] == "600002"
