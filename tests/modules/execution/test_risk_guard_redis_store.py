"""Redis-backed Risk Guard snapshot persistence."""

from __future__ import annotations

from app.modules.execution.services.risk_guard_service import AccountRiskSnapshot


class _FakeRedis:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value: str, ex: int | None = None):
        self._data[key] = value
        return True


def test_redis_store_roundtrip():
    from app.infrastructure.trading.risk_guard_redis_store import RedisRiskGuardStore

    fake = _FakeRedis()
    store = RedisRiskGuardStore(client=fake, key_prefix="test:rg:")
    snap = AccountRiskSnapshot(
        equity=95_000.0,
        day_start_equity=100_000.0,
        consecutive_stop_outs=2,
        execution_suspended=True,
    )
    store.set_snapshot("acc-a", snap)
    loaded = store.get_snapshot("acc-a")
    assert loaded.equity == 95_000.0
    assert loaded.day_start_equity == 100_000.0
    assert loaded.consecutive_stop_outs == 2
    assert loaded.execution_suspended is True


def test_redis_store_default_when_missing():
    from app.infrastructure.trading.risk_guard_redis_store import RedisRiskGuardStore

    store = RedisRiskGuardStore(client=_FakeRedis())
    loaded = store.get_snapshot("missing")
    assert loaded.equity == 100_000.0
    assert loaded.execution_suspended is False
