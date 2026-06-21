from __future__ import annotations
"""标准行情连接（pytdx.hq.TdxHq_API）。"""


import threading
import time
from typing import Any

from app.core.logger import get_logger
from app.infrastructure.external.tdx_selector import TdxBestServersConnect
from app.infrastructure.pytdx.exceptions import PytdxConnectionError
from app.infrastructure.pytdx.runtime import import_hq_api, pytdx_available

logger = get_logger(__name__)


class TdxHqConnection:
    """单例 + 心跳 + 服务器池故障转移（对齐原 TdxConnectionManager）。"""

    _instance: TdxHqConnection | None = None
    _init_lock = threading.Lock()

    def __new__(cls) -> TdxHqConnection:
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_once()
            return cls._instance

    def _init_once(self) -> None:
        if getattr(self, "_ready", False):
            return
        self._ready = True
        self._api = import_hq_api()(raise_exception=False)
        self.is_connected = False
        self._server_selector = TdxBestServersConnect()
        self._server_pool: list[tuple[str, int]] = []
        self._current_server_idx = 0
        self._lock = threading.RLock()
        self._last_reconnect = 0.0
        self._reconnect_cooldown = 15.0
        self._start_heartbeat()
        self.reconnect()

    def _start_heartbeat(self) -> None:
        def loop() -> None:
            while True:
                time.sleep(60)
                with self._lock:
                    if self.is_connected:
                        try:
                            self._api.get_security_count(0)
                        except Exception:
                            self.is_connected = False
                            self.reconnect()
                    else:
                        self.reconnect()

        threading.Thread(target=loop, daemon=True, name="tdx-hq-heartbeat").start()

    def reconnect(self) -> bool:
        with self._lock:
            now = time.time()
            if now - self._last_reconnect < self._reconnect_cooldown and self.is_connected:
                return True
            self._last_reconnect = now
            try:
                self._api.disconnect()
            except Exception as e:
                logger.warning("connection_hq.py.reconnect: %s", e)
            if not self._server_pool:
                best = self._server_selector.get_best_tdx_servers()
                self._server_pool = [(s["ip"], int(s["port"])) for s in best] if best else []
            if not self._server_pool:
                self.is_connected = False
                return False
            for _ in range(len(self._server_pool)):
                ip, port = self._server_pool[self._current_server_idx]
                try:
                    if self._api.connect(ip, port, time_out=5):
                        self.is_connected = True
                        logger.info("TDX HQ connected %s:%s", ip, port)
                        return True
                except Exception as exc:
                    logger.debug("TDX HQ connect failed %s:%s %s", ip, port, exc)
                self._current_server_idx = (self._current_server_idx + 1) % len(self._server_pool)
            self.is_connected = False
            return False

    @property
    def api(self) -> Any:
        return self._api

    def execute(self, method: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if not self.is_connected and not self.reconnect():
                raise PytdxConnectionError("TDX HQ connection failed")
            func = getattr(self._api, method, None)
            if not callable(func):
                raise AttributeError(f"unknown hq method: {method}")
            try:
                result = func(*args, **kwargs)
                if result is None:
                    self.is_connected = False
                    if self.reconnect():
                        result = func(*args, **kwargs)
                return result
            except Exception as exc:
                self.is_connected = False
                raise RuntimeError(f"TDX HQ {method} failed: {exc}") from exc

    def status(self) -> dict[str, Any]:
        with self._lock:
            ip, port = (
                self._server_pool[self._current_server_idx]
                if self._server_pool
                else ("", 0)
            )
            return {
                "module": "hq",
                "available": pytdx_available(),
                "connected": self.is_connected,
                "server": {"ip": ip, "port": port},
                "pool_size": len(self._server_pool),
            }
