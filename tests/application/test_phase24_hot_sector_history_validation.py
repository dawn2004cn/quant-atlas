"""Phase 24: history row validation, hot sector deps, factor decay logging."""

from __future__ import annotations

from typing import Any

import pytest

from app.application.errors import ValidationError
from app.modules.data.services.history_row_validator import validate_ohlcv_history_rows
from app.modules.market_data.services.hot_sector_storage_service import HotSectorStorageService
from app.modules.data.services.forward_testing_service import FactorDecayMonitor
from app.presentation.api.route_deps import HotSectorRouteDeps, require_hot_sector_storage_service


def test_validate_ohlcv_history_rows_normalizes_row() -> None:
    rows = validate_ohlcv_history_rows(
        [
            {
                "date": "2026-01-15T00:00:00",
                "open": "1.5",
                "high": 2,
                "low": 1,
                "close": 1.8,
                "volume": 100,
            }
        ]
    )
    assert rows[0]["date"] == "2026-01-15"
    assert rows[0]["open"] == 1.5
    assert rows[0]["amount"] == 0.0


def test_validate_ohlcv_history_rows_rejects_missing_close() -> None:
    with pytest.raises(ValidationError) as exc:
        validate_ohlcv_history_rows([{"date": "2026-01-15", "open": 1, "high": 2, "low": 1}])
    assert exc.value.message == "invalid_row_field"


def test_hot_sector_route_deps_require_service() -> None:
    svc = HotSectorStorageService(settings=object(), repository=None)
    resolved = require_hot_sector_storage_service(
        HotSectorRouteDeps(hot_sector_storage_service=svc),
    )
    assert resolved is svc


def test_hot_sector_route_deps_missing_service_raises() -> None:
    with pytest.raises(ValidationError) as exc:
        require_hot_sector_storage_service(HotSectorRouteDeps(hot_sector_storage_service=None))
    assert exc.value.message == "hot_sector_storage_service_unavailable"


def test_factor_decay_monitor_logs_sync_decay_event() -> None:
    logged: list[tuple[str, dict[str, Any]]] = []

    class _FakeFactorRepo:
        def get_factor(self, factor_id: str) -> dict[str, Any]:
            return {"factor_id": factor_id, "ir": 0.2, "ic_mean": 0.01, "decay_rate": 0.1}

        def log_decay_event(self, **kwargs: Any) -> int:
            logged.append((str(kwargs.get("factor_id") or ""), kwargs))
            return 1

    monitor = FactorDecayMonitor(_FakeFactorRepo(), ir_threshold=0.5)
    assert monitor.check_decay("alpha1") is True
    assert logged
    assert logged[0][0] == "alpha1"
    assert logged[0][1]["severity"] == "critical"
