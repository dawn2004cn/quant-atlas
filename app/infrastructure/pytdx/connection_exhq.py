from __future__ import annotations
"""扩展行情连接（pytdx.exhq.TdxExHq_API）。"""


import threading
from typing import Any

from app.core.logger import get_logger
from app.infrastructure.pytdx.exceptions import PytdxConnectionError
from app.infrastructure.pytdx.runtime import import_exhq_api, pytdx_available

logger = get_logger(__name__)

# 扩展行情常用服务器（期货/外盘）
_DEFAULT_EXHQ_SERVERS: list[tuple[str, int]] = [
    ("116.205.143.214", 7727),
    ("47.102.108.214", 7727),
    ("120.25.218.6", 7727),
    ("112.74.214.43", 7727),
]


class TdxExHqConnection:
    _instance: TdxExHqConnection | None = None
    _init_lock = threading.Lock()

    def __new__(cls) -> TdxExHqConnection:
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_once()
            return cls._instance

    def _init_once(self) -> None:
        if getattr(self, "_ready", False):
            return
        self._ready = True
        self._api = import_exhq_api()(raise_exception=False)
        self.is_connected = False
        self._servers = list(_DEFAULT_EXHQ_SERVERS)
        self._idx = 0
        self._lock = threading.RLock()
        self.reconnect()

    def reconnect(self) -> bool:
        with self._lock:
            try:
                self._api.disconnect()
            except Exception as e:
                logger.warning("connection_exhq.py.reconnect: %s", e)
            for _ in range(len(self._servers)):
                ip, port = self._servers[self._idx]
                try:
                    if self._api.connect(ip, port, time_out=5):
                        self.is_connected = True
                        logger.info("TDX EXHQ connected %s:%s", ip, port)
                        return True
                except Exception as exc:
                    logger.debug("TDX EXHQ connect failed %s:%s %s", ip, port, exc)
                self._idx = (self._idx + 1) % len(self._servers)
            self.is_connected = False
            return False

    def execute(self, method: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if not self.is_connected and not self.reconnect():
                raise PytdxConnectionError("TDX EXHQ connection failed")
            func = getattr(self._api, method, None)
            if not callable(func):
                raise AttributeError(f"unknown exhq method: {method}")
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                self.is_connected = False
                raise RuntimeError(f"TDX EXHQ {method} failed: {exc}") from exc

    def status(self) -> dict[str, Any]:
        with self._lock:
            ip, port = self._servers[self._idx] if self._servers else ("", 0)
            return {
                "module": "exhq",
                "available": pytdx_available(),
                "connected": self.is_connected,
                "server": {"ip": ip, "port": port},
            }
