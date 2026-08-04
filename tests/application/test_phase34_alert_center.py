"""Phase 34 UX-2: intelligent alert center aggregation."""

from __future__ import annotations

from app.modules.system.services.system.alert_center_service import AlertCenterService


class _FakeStore:
    def __init__(self, items: list[dict]) -> None:
        self._items = items

    def list_recent(self, *, limit: int = 80) -> list[dict]:
        return self._items[:limit]


def test_alert_center_collects_factor_and_task_failure_alerts(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 0},
    )
    store = _FakeStore(
        [
            {
                "id": "1",
                "ts": "2026-05-23T10:00:00Z",
                "event": "factor_ic_alert",
                "task_id": "ic-1",
                "task_name": "app.tasks.factor_ic_alerts.factor_ic_monitor_tick",
                "label": "因子监控·IC 弱信号巡检",
                "detail": "弱 |IC| 因子 3 个",
                "meta": {"weak_ic_lag1_count": 3},
            },
            {
                "id": "2",
                "ts": "2026-05-23T09:00:00Z",
                "event": "task_failed",
                "task_id": "t-2",
                "task_name": "app.tasks.market_tasks.scheduled_longhu",
                "label": "龙虎榜",
                "detail": "connection timeout",
                "meta": {},
            },
        ]
    )
    service = AlertCenterService(
        message_store_factory=lambda: store,
        freshness_checker=lambda _table, _minutes=15: True,
    )
    feed = service.list_alerts(limit=10, include_system_probes=False)
    assert feed.total == 2
    assert feed.counts_by_level.get("critical") == 1
    assert feed.counts_by_category.get("factor") == 1


def test_alert_center_adds_data_freshness_warning(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 0},
    )
    service = AlertCenterService(
        message_store_factory=lambda: _FakeStore([]),
        freshness_checker=lambda _table, _minutes=15: False,
    )
    feed = service.list_alerts(limit=10, include_system_probes=False)
    assert feed.total >= 1
    assert any(item.category == "data" for item in feed.items)


def test_alert_center_respects_min_level_filter(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 0},
    )
    store = _FakeStore(
        [
            {
                "id": "1",
                "ts": "2026-05-23T10:00:00Z",
                "event": "factor_ic_alert",
                "task_id": "ic-1",
                "task_name": "x",
                "label": "IC",
                "detail": "weak",
                "meta": {},
            }
        ]
    )
    service = AlertCenterService(
        message_store_factory=lambda: store,
        freshness_checker=lambda _table, _minutes=15: True,
    )
    feed = service.list_alerts(limit=10, min_level="critical", include_system_probes=False)
    assert feed.total == 0
    assert all(item.level == "critical" for item in feed.items)


def test_alert_center_includes_quotes_dump_warning(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {
            "full_dump_count": 4,
            "last_full_dump_at": "2026-08-03T12:00:00Z",
            "last_full_dump_market": "CN",
            "last_full_dump_rows": 5000,
            "backend": "memory",
        },
    )
    monkeypatch.setattr(
        "app.core.runtime_config.get_runtime_int",
        lambda key, default=0: 2 if "THRESHOLD" in key else default,
    )
    service = AlertCenterService(
        message_store_factory=lambda: _FakeStore([]),
        freshness_checker=lambda _table, _minutes=15: True,
    )
    feed = service.list_alerts(limit=10, include_system_probes=False)
    dump_items = [i for i in feed.items if i.id == "data:quotes:full_dump"]
    assert len(dump_items) == 1
    assert dump_items[0].category == "data"
    assert dump_items[0].level == "warning"
    assert "quotes/page" in dump_items[0].message
    assert dump_items[0].meta.get("action_url") == "/observability"
