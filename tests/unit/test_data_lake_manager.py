"""Unit tests for DataLakeManager Phase A API closure."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.core.mesh.unified_data_lake import DataQuery, DataScope
from app.modules.data.services.data_lake_manager import DataLakeManager


@pytest.mark.asyncio
async def test_get_data_returns_firewall_warnings_on_empty(tmp_path, monkeypatch):
    manager = DataLakeManager(registry=None)
    query = DataQuery(
        symbol="600519",
        market="CN",
        start_date=datetime.now() - timedelta(days=5),
        end_date=datetime.now(),
        scope=DataScope.HISTORICAL,
    )
    df, warnings = await manager.get_data(query)
    assert isinstance(df, pd.DataFrame)
    assert any("Empty" in w or "Lake miss" in w for w in warnings)


def test_get_system_health_shape():
    manager = DataLakeManager(registry=None)
    health = manager.get_system_health()
    assert "status" in health
    assert "engine" in health
    assert "metrics" in health
    assert "p95_latency_ms" in health["metrics"]


@pytest.mark.asyncio
async def test_get_data_market_fallback(monkeypatch):
    registry = MagicMock()
    market_svc = MagicMock()
    market_svc.get_history.return_value = [
        {"date": "2026-01-01", "close": 100.0},
        {"date": "2026-01-02", "close": 101.0},
    ]
    registry.get_or_none.return_value = market_svc
    manager = DataLakeManager(registry=registry)
    query = DataQuery(
        symbol="600519",
        market="CN",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 2),
        scope=DataScope.HISTORICAL,
    )
    df, warnings = await manager.get_data(query)
    assert not df.empty
    assert "close" in df.columns
    assert any("market" in w.lower() for w in warnings)
