from __future__ import annotations

"""Pluggable mesh transports — Redis Pub/Sub (default) and in-memory (tests)."""

import json
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.core.mesh.protocol import MESH_EVENTS_CHANNEL

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, dict[str, Any]], None]


class MeshTransport(ABC):
    @abstractmethod
    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        ...

    @abstractmethod
    def subscribe(self, channel: str, handler: MessageHandler) -> None:
        ...

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @property
    @abstractmethod
    def backend(self) -> str:
        ...


class MemoryMeshTransport(MeshTransport):
    """In-process transport for unit tests and local dev without Redis."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._lock = threading.Lock()

    @property
    def backend(self) -> str:
        return "memory"

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        with self._lock:
            handlers = list(self._handlers.get(channel, []))
            if channel != MESH_EVENTS_CHANNEL:
                handlers.extend(self._handlers.get(MESH_EVENTS_CHANNEL, []))
        for handler in handlers:
            try:
                handler(channel, message)
            except Exception as exc:
                logger.warning("memory mesh handler error: %s", exc)
        return True

    def subscribe(self, channel: str, handler: MessageHandler) -> None:
        with self._lock:
            self._handlers.setdefault(channel, []).append(handler)

    def start(self) -> None:
        return

    def stop(self) -> None:
        with self._lock:
            self._handlers.clear()


class RedisMeshTransport(MeshTransport):
    """Redis Pub/Sub mesh transport with auto-reconnect."""

    _RECONNECT_DELAY_SECONDS = 5.0
    _MAX_RECONNECT_DELAY = 60.0

    def __init__(self, redis_url: str) -> None:
        self._url = (redis_url or "").strip()
        self._redis: Any = None
        self._pub: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._lock = threading.Lock()
        self._health = {
            "connected": False,
            "publish_count": 0,
            "publish_failures": 0,
            "receive_count": 0,
            "reconnect_count": 0,
            "last_error": None,
            "last_connect_at": None,
            "last_publish_at": None,
        }

    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "redis_unavailable"

    @property
    def health(self) -> dict[str, Any]:
        return dict(self._health)

    def _connect(self) -> bool:
        if self._redis is not None:
            return True
        if not self._url:
            return False
        try:
            import redis

            self._redis = redis.Redis.from_url(self._url, decode_responses=True)
            self._pub = redis.Redis.from_url(self._url, decode_responses=False)
            self._redis.ping()
            self._health["connected"] = True
            self._health["last_connect_at"] = threading.current_thread().name
            from datetime import datetime, timezone
            self._health["last_connect_at"] = datetime.now(timezone.utc).isoformat()
            self._health["last_error"] = None
            return True
        except Exception as exc:
            self._health["connected"] = False
            self._health["last_error"] = str(exc)
            logger.warning("Redis mesh transport unavailable: %s", exc)
            self._redis = None
            self._pub = None
            return False

    def _disconnect(self) -> None:
        self._health["connected"] = False
        self._redis = None
        self._pub = None

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        if not self._connect() or self._pub is None:
            self._health["publish_failures"] += 1
            return False
        try:
            payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
            receivers = self._pub.publish(channel, payload)
            self._health["publish_count"] += 1
            from datetime import datetime, timezone
            self._health["last_publish_at"] = datetime.now(timezone.utc).isoformat()
            return int(receivers or 0) >= 0
        except Exception as exc:
            self._health["publish_failures"] += 1
            self._health["last_error"] = str(exc)
            self._disconnect()
            logger.warning("mesh redis publish failed: %s", exc)
            return False

    def subscribe(self, channel: str, handler: MessageHandler) -> None:
        with self._lock:
            self._handlers.setdefault(channel, []).append(handler)

    def start(self) -> None:
        if not self._connect() or self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._listen_loop, name="mesh-redis-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._disconnect()

    def _listen_loop(self) -> None:
        reconnect_delay = 0.0
        while not self._stop.is_set():
            if self._redis is None:
                self._health["reconnect_count"] += 1
                if not self._connect():
                    wait = min(reconnect_delay or self._RECONNECT_DELAY_SECONDS, self._MAX_RECONNECT_DELAY)
                    reconnect_delay = min(wait * 2, self._MAX_RECONNECT_DELAY)
                    self._stop.wait(wait)
                    continue
                reconnect_delay = 0.0

            try:
                pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
                with self._lock:
                    channels = list(self._handlers.keys())
                if not channels:
                    pubsub.subscribe(MESH_EVENTS_CHANNEL)
                else:
                    pubsub.subscribe(*channels)
                while not self._stop.is_set():
                    msg = pubsub.get_message(timeout=1.0)
                    if not msg or msg.get("type") != "message":
                        continue
                    self._health["receive_count"] += 1
                    channel = str(msg.get("channel") or MESH_EVENTS_CHANNEL)
                    raw = msg.get("data")
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="replace")
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    with self._lock:
                        handlers = list(self._handlers.get(channel, []))
                        if channel != MESH_EVENTS_CHANNEL:
                            handlers.extend(self._handlers.get(MESH_EVENTS_CHANNEL, []))
                    for handler in handlers:
                        try:
                            handler(channel, data)
                        except Exception as exc:
                            logger.warning("mesh redis handler: %s", exc)
            except Exception as exc:
                self._health["last_error"] = str(exc)
                self._disconnect()
                logger.warning("mesh redis listener disconnected: %s", exc)
                if not self._stop.is_set():
                    wait = min(reconnect_delay or self._RECONNECT_DELAY_SECONDS, self._MAX_RECONNECT_DELAY)
                    reconnect_delay = min(wait * 2, self._MAX_RECONNECT_DELAY)
                    self._stop.wait(wait)


class NATSMeshTransport(MeshTransport):
    """NATS Pub/Sub mesh transport (optional nats-py dependency)."""

    def __init__(self, nats_url: str) -> None:
        self._url = (nats_url or "").strip()
        self._nc: Any = None
        self._sub: Any = None
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._lock = threading.Lock()
        self._loop: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def backend(self) -> str:
        return "nats" if self._nc is not None else "nats_unavailable"

    def _connect(self) -> bool:
        if self._nc is not None:
            return True
        if not self._url:
            return False
        try:
            import asyncio

            import nats

            loop = asyncio.new_event_loop()

            async def _open() -> Any:
                return await nats.connect(self._url)

            self._nc = loop.run_until_complete(_open())
            self._loop = loop
            return True
        except Exception as exc:
            logger.warning("NATS mesh transport unavailable: %s", exc)
            self._nc = None
            self._loop = None
            return False

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        if not self._connect() or self._nc is None or self._loop is None:
            return False
        try:
            import asyncio

            payload = json.dumps(message, ensure_ascii=False).encode("utf-8")

            async def _pub() -> None:
                await self._nc.publish(channel, payload)

            asyncio.run_coroutine_threadsafe(_pub(), self._loop).result(timeout=5.0)
            return True
        except Exception as exc:
            logger.warning("mesh nats publish failed: %s", exc)
            return False

    def subscribe(self, channel: str, handler: MessageHandler) -> None:
        with self._lock:
            self._handlers.setdefault(channel, []).append(handler)

    def start(self) -> None:
        if not self._connect() or self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._listen_loop, name="mesh-nats-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._nc is not None and self._loop is not None:
            try:
                import asyncio

                async def _close() -> None:
                    await self._nc.drain()
                    await self._nc.close()

                asyncio.run_coroutine_threadsafe(_close(), self._loop).result(timeout=3.0)
            except Exception as exc:
                logger.debug("mesh nats close: %s", exc)
        self._nc = None
        self._loop = None
        with self._lock:
            self._handlers.clear()

    def _listen_loop(self) -> None:
        if self._nc is None or self._loop is None:
            return
        try:
            import asyncio

            async def _subscribe_all() -> None:
                with self._lock:
                    channels = list(self._handlers.keys()) or [MESH_EVENTS_CHANNEL]

                async def _on_msg(msg: Any) -> None:
                    channel = str(getattr(msg, "subject", "") or MESH_EVENTS_CHANNEL)
                    raw = getattr(msg, "data", b"")
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="replace")
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        return
                    with self._lock:
                        handlers = list(self._handlers.get(channel, []))
                        if channel != MESH_EVENTS_CHANNEL:
                            handlers.extend(self._handlers.get(MESH_EVENTS_CHANNEL, []))
                    for handler in handlers:
                        try:
                            handler(channel, data)
                        except Exception as exc:
                            logger.warning("mesh nats handler: %s", exc)

                for ch in channels:
                    await self._nc.subscribe(ch, cb=_on_msg)
                while not self._stop.is_set():
                    await asyncio.sleep(0.25)

            asyncio.run_coroutine_threadsafe(_subscribe_all(), self._loop).result(timeout=5.0)
            while not self._stop.is_set():
                self._stop.wait(0.5)
        except Exception as exc:
            logger.warning("mesh nats listener stopped: %s", exc)


def create_mesh_transport(
    redis_url: str | None,
    *,
    force_memory: bool = False,
    transport_kind: str | None = None,
    nats_url: str | None = None,
) -> MeshTransport:
    if force_memory:
        return MemoryMeshTransport()

    kind = (transport_kind or "").strip().lower()
    if not kind:
        try:
            from app.core.runtime_config import get_runtime

            kind = (get_runtime("MESH_TRANSPORT", "redis") or "redis").strip().lower()
        except Exception:
            kind = "redis"

    if kind == "memory":
        return MemoryMeshTransport()

    if kind == "nats":
        url = (nats_url or "").strip()
        if not url:
            try:
                from app.core.runtime_config import get_runtime

                url = (get_runtime("MESH_NATS_URL", "nats://127.0.0.1:4222") or "").strip()
            except Exception:
                url = "nats://127.0.0.1:4222"
        transport = NATSMeshTransport(url)
        if transport._connect():
            return transport
        logger.info("mesh falling back to memory transport (nats unavailable)")
        return MemoryMeshTransport()

    if not (redis_url or "").strip():
        return MemoryMeshTransport()
    transport = RedisMeshTransport(redis_url)
    if transport._connect():
        return transport
    logger.info("mesh falling back to memory transport")
    return MemoryMeshTransport()


__all__ = [
    "MeshTransport",
    "MemoryMeshTransport",
    "RedisMeshTransport",
    "NATSMeshTransport",
    "create_mesh_transport",
]
