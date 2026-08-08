from __future__ import annotations
"""定时刷新龙虎榜 / 研报（守护线程，不阻塞 Flask）。"""


import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.core.logger import get_logger

if TYPE_CHECKING:
    from .basic_market_data_service import BasicMarketDataService

logger = get_logger(__name__)


class BasicDataScheduler:
    """按本地时钟在 06:xx 抓研报、17:xx 抓龙虎榜；启动后先延迟做一次轻量补齐。"""

    def __init__(self, service: BasicMarketDataService) -> None:
        self._svc = service
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_longhu_day: str | None = None
        self._last_yanbao_day: str | None = None
        self._warm_done = False
        self._t0 = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="basic-data-scheduler", daemon=True)
        self._thread.start()
        logger.info("BasicDataScheduler started")

    def stop(self, join_timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=join_timeout)

    def _run(self) -> None:
        self._t0 = time.monotonic()
        while not self._stop.is_set():
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            h, m = now.hour, now.minute

            if not self._warm_done and (time.monotonic() - self._t0) > 120.0:
                self._warm_done = True
                try:
                    self._svc.ingest_longhu_em(lookback_calendar_days=10)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("warm longhu: %s", exc)

            # 17:00–17:20 龙虎榜
            if h == 17 and m < 20 and self._last_longhu_day != today:
                try:
                    r = self._svc.ingest_longhu_em(lookback_calendar_days=14)
                    if r.get("ok"):
                        self._last_longhu_day = today
                        logger.info("scheduled longhu ok rows=%s", r.get("rows"))
                except Exception as exc:  # noqa: BLE001
                    logger.exception("scheduled longhu failed")

            # 06:00–06:30 研报
            if h == 6 and m < 30 and self._last_yanbao_day != today:
                try:
                    r = self._svc.ingest_yanbao_eastmoney_html()
                    if r.get("ok"):
                        self._last_yanbao_day = today
                        logger.info("scheduled yanbao ok rows=%s", r.get("rows"))
                except Exception as exc:  # noqa: BLE001
                    logger.exception("scheduled yanbao failed")

            time.sleep(45)
