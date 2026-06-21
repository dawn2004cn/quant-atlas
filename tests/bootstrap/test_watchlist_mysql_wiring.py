"""Watchlist / stock-group factories should prefer MySQL when configured."""

from __future__ import annotations

import pytest

from app.bootstrap import create_app
from app.config import get_settings


@pytest.mark.skipif(not get_settings().use_mysql, reason="MySQL not enabled")
def test_watchlist_services_use_mysql_repositories() -> None:
    app = create_app()
    watchlist = app.services.watchlist_service
    stock_group = app.services.stock_group_service

    assert watchlist is not None
    assert stock_group is not None

    watchlist_repo_cls = type(watchlist._repository).__name__
    stock_group_repo_cls = type(stock_group._repository).__name__

    assert watchlist_repo_cls == "MySQLWatchlistRepository", watchlist_repo_cls
    assert stock_group_repo_cls == "MySQLStockGroupRepository", stock_group_repo_cls
