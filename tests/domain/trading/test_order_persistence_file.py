"""Order persistence backend tests (file / SQLite / Redis)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.domain.trading.order_persistence import OrderPersistence
from app.domain.trading.order_persistence_file import FileOrderPersistenceBackend
from app.infrastructure.trading.order_persistence_redis import RedisOrderPersistenceBackend
from app.domain.trading.order_persistence_sqlite import SqliteOrderPersistenceBackend


def test_file_backend_round_trip(tmp_path):
    state_file = tmp_path / "order_state.json"
    events_file = tmp_path / "order_events.jsonl"
    backend = FileOrderPersistenceBackend(state_file, events_file)

    assert backend.save_state({"o1": {"state": "open", "qty": 100}})
    assert backend.load_state() == {"o1": {"state": "open", "qty": 100}}

    assert backend.append_event({"order_id": "o1", "type": "fill"})
    events = backend.load_events("o1")
    assert len(events) == 1
    assert events[0]["type"] == "fill"


def test_order_persistence_file_backend_integration(tmp_path):
    persistence = OrderPersistence(backend="file", path=str(tmp_path))
    assert persistence.save_state({"o2": {"state": "pending"}})
    loaded = persistence.load_state()
    assert loaded["o2"]["state"] == "pending"
    assert persistence.save_event({"order_id": "o2", "type": "ack"})
    assert persistence.load_events("o2")[0]["type"] == "ack"


def test_sqlite_backend_round_trip(tmp_path):
    backend = SqliteOrderPersistenceBackend(tmp_path / "orders.db")
    assert backend.save_state({"o3": {"state": "filled", "qty": 50}})
    assert backend.load_state()["o3"]["qty"] == 50


def test_order_persistence_sqlite_integration(tmp_path):
    persistence = OrderPersistence(backend="sqlite", path=str(tmp_path))
    assert persistence.save_state({"o4": {"state": "open"}})
    assert persistence.load_state()["o4"]["state"] == "open"


def test_redis_backend_round_trip():
    store: dict[bytes, bytes] = {}
    client = MagicMock()
    pipe = MagicMock()
    client.pipeline.return_value = pipe

    def _hset(_name: str, key: str, value: str) -> None:
        store[key.encode()] = value.encode()

    pipe.hset.side_effect = _hset
    pipe.execute.return_value = None
    client.hgetall.return_value = store

    backend = RedisOrderPersistenceBackend(client=client)
    payload = {"o5": {"state": "partial", "qty": 10}}
    assert backend.save_state(payload)
    loaded = backend.load_state()
    assert loaded["o5"]["qty"] == 10
    assert json.loads(store[b"o5"].decode())["state"] == "partial"


def test_order_persistence_redis_integration():
    store: dict[bytes, bytes] = {}
    client = MagicMock()
    pipe = MagicMock()
    client.pipeline.return_value = pipe
    pipe.hset.side_effect = lambda _n, k, v: store.update({k.encode(): v.encode()})
    pipe.execute.return_value = None
    client.hgetall.return_value = store

    persistence = OrderPersistence(backend="redis", path="data/orders")
    persistence._redis_backend = RedisOrderPersistenceBackend(client=client)
    assert persistence.save_state({"o6": {"state": "done"}})
    assert persistence.load_state()["o6"]["state"] == "done"
