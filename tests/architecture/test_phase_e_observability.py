"""Phase E — observability snapshot, billing placeholder, CI collection fix."""

from __future__ import annotations

from types import SimpleNamespace


def test_observability_snapshot_builds():
    from app.modules.system.services.system.observability_snapshot_service import (
        ObservabilitySnapshotService,
    )
    from app.presentation.api.v1_context import ApiV1Context

    ctx = ApiV1Context(
        market_service=object(),
        stock_service=object(),
        watchlist_service=object(),
        stock_group_service=object(),
        daily_workbench_service=object(),
        recommendation_service=object(),
        task_message_store=object(),
    )
    snap = ObservabilitySnapshotService().build_snapshot(ctx)
    assert snap["overall_status"] in ("ok", "degraded", "critical")
    assert snap["pulse"]["components"]
    assert snap["sla"]["uptime_target_pct"] == 99.0
    assert snap["critical_services"]["ok"] is True
    assert "quotes_api" in snap
    assert "full_dump_count" in snap["quotes_api"]
    assert "trend_rows" in snap["quotes_api"]
    assert "quotes_full_dump_warn" in snap["health_banner"]
    assert "alert_ops" in snap
    assert "quotes_dump_monitor_beat" in snap["alert_ops"]
    assert "preferred_endpoint" in snap["alert_ops"]


def test_health_banner_quotes_dump_threshold(monkeypatch):
    from app.modules.system.services.system.system_health_banner_service import (
        SystemHealthBannerService,
    )

    monkeypatch.setattr(
        "app.modules.system.services.system.system_health_banner_service.get_runtime_int",
        lambda key, default=0: 2 if "THRESHOLD" in key else default,
    )

    class _EmptyAlerts:
        counts_by_level = {"critical": 0, "warning": 0}
        items = []

    class _AlertSvc:
        def list_alerts(self, **kwargs):
            return _EmptyAlerts()

    banner = SystemHealthBannerService(alert_service=_AlertSvc()).build_banner(
        quotes_dump={"full_dump_count": 3},
    )
    assert banner["quotes_full_dump_warn"] is True
    assert banner["level"] == "warning"
    assert "quotes/page" in banner["message"]
    assert banner["quotes_full_dump_count"] == 3
    assert banner["quotes_full_dump_threshold"] == 2

    ok_banner = SystemHealthBannerService(alert_service=_AlertSvc()).build_banner(
        quotes_dump={"full_dump_count": 1},
    )
    assert ok_banner["quotes_full_dump_warn"] is False


def test_workbench_health_banner_injects_quotes_dump(monkeypatch):
    from app.modules.strategy.services.analytics.daily_workbench_service import (
        DailyWorkbenchService,
    )
    from app.modules.system.services.system.system_health_banner_service import (
        SystemHealthBannerService,
    )

    monkeypatch.setattr(
        "app.modules.market_data.services.quotes_dump_metrics.get_quotes_dump_stats",
        lambda: {"full_dump_count": 5, "symbol_batch_count": 0},
    )
    monkeypatch.setattr(
        "app.modules.system.services.system.system_health_banner_service.get_runtime_int",
        lambda key, default=0: 1 if "THRESHOLD" in key else default,
    )

    class _EmptyAlerts:
        counts_by_level = {"critical": 0, "warning": 0}
        items = []

    class _AlertSvc:
        def list_alerts(self, **kwargs):
            return _EmptyAlerts()

    svc = DailyWorkbenchService(
        market_service=object(),
        watchlist_service=object(),
        health_banner_service=SystemHealthBannerService(alert_service=_AlertSvc()),
    )
    banner = svc._build_health_banner(integration={}, task_digest={})
    assert banner["quotes_full_dump_warn"] is True
    assert banner["quotes_full_dump_count"] == 5
    assert banner.get("headline")
    assert "quotes/page" in (banner.get("summary") or banner.get("message") or "")


def test_quotes_dump_metrics_record_and_reset():
    from app.modules.market_data.services.quotes_dump_metrics import (
        get_quotes_dump_stats,
        record_full_dump,
        record_symbol_batch,
        reset_quotes_dump_stats,
    )

    reset_quotes_dump_stats()
    record_full_dump(market="CN", rows=120)
    record_symbol_batch(market="CN", symbols=8)
    stats = get_quotes_dump_stats()
    assert stats["full_dump_count"] == 1
    assert stats["symbol_batch_count"] == 1
    assert stats["last_full_dump_market"] == "CN"
    assert stats["last_full_dump_rows"] == 120
    assert stats["backend"] in {"memory", "redis"}
    assert stats["trend_rows"] == [120]
    assert len(stats["recent_dumps"]) == 1
    reset_quotes_dump_stats()
    assert get_quotes_dump_stats()["full_dump_count"] == 0
    assert get_quotes_dump_stats()["trend_rows"] == []


def test_quotes_dump_metrics_redis_backend(monkeypatch):
    """When Redis is available, counters persist via hash (cross-process)."""
    from app.modules.market_data.services import quotes_dump_metrics as m

    store: dict[str, str] = {}
    history: list[str] = []

    class _FakePipe:
        def __init__(self) -> None:
            self._ops: list = []

        def hincrby(self, key, field, amount):
            self._ops.append(("hincrby", key, field, amount))
            return self

        def hset(self, key, mapping=None, **kwargs):
            self._ops.append(("hset", key, mapping or kwargs))
            return self

        def lpush(self, key, value):
            self._ops.append(("lpush", key, value))
            return self

        def ltrim(self, key, start, stop):
            self._ops.append(("ltrim", key, start, stop))
            return self

        def expire(self, key, ttl):
            self._ops.append(("expire", key, ttl))
            return self

        def execute(self):
            for op in self._ops:
                if op[0] == "hincrby":
                    _, _k, field, amount = op
                    store[field] = str(int(store.get(field) or 0) + int(amount))
                elif op[0] == "hset":
                    _, _k, mapping = op
                    for fk, fv in mapping.items():
                        store[fk] = str(fv)
                elif op[0] == "lpush":
                    _, _k, value = op
                    history.insert(0, value)
                elif op[0] == "ltrim":
                    _, _k, start, stop = op
                    del history[stop + 1 :]
                    if start:
                        del history[:start]
            self._ops.clear()
            return []

    class _FakeRedis:
        def pipeline(self):
            return _FakePipe()

        def hgetall(self, key):
            return dict(store)

        def lrange(self, key, start, stop):
            end = None if stop < 0 else stop + 1
            return list(history[start:end])

        def delete(self, *keys):
            store.clear()
            history.clear()
            return len(keys)

        def expire(self, key, ttl):
            return True

    monkeypatch.setattr(m, "_redis_client", lambda: _FakeRedis())
    m.reset_quotes_dump_stats()
    m.record_full_dump(market="CN", rows=50)
    m.record_full_dump(market="CN", rows=80)
    stats = m.get_quotes_dump_stats()
    assert stats["backend"] == "redis"
    assert stats["full_dump_count"] == 2
    assert stats["last_full_dump_rows"] == 80
    assert stats["trend_rows"] == [50, 80]
    assert len(stats["recent_dumps"]) == 2
    m.reset_quotes_dump_stats()
    assert m.get_quotes_dump_stats()["full_dump_count"] == 0


def test_billing_status_beta():
    from app.domain.billing.retail_billing import build_billing_status

    status = build_billing_status(SimpleNamespace(role="free"))
    assert status["enabled"] is False
    assert status["provider"] == "stripe"
    assert status["tier"] == "free"


def test_billing_status_pro_tier():
    from app.domain.billing.retail_billing import build_billing_status

    status = build_billing_status(SimpleNamespace(role="pro"))
    assert status["tier"] == "pro"
    assert status["checkout_available"] is False
