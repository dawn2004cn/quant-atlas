from __future__ import annotations
"""Background scanner service with priority queues and health monitoring."""


import threading
import time
from datetime import datetime

from app.domain.ports import MarketDataProvider
from app.domain.ports.stock_cache_port import StockCachePort
from app.core.logger import get_logger
from app.core.utils.datetime_utils import is_trading_time_cn
from app.application.dto.scanner_dto import ScannerStatusDTO, ScanResultDTO

logger = get_logger(__name__)

# 核心权重股 (CSI 300 / SSE 50 Sample)
CORE_TICKERS = [
    "600519", "601318", "000001", "000858", "600036", "300750", "601166", "600276",
    "002594", "002415", "601888", "000333", "600900", "601398", "000651", "600030",
    "000002", "601088", "000725", "601628", "601169", "002352", "600016", "601988"
]


class ScannerApplicationService:
    """Advanced background scanner with structured logging."""

    def __init__(self, market_provider: MarketDataProvider, stock_cache: StockCachePort):
        self._provider = market_provider
        self._cache = stock_cache
        self._is_running = False
        self._threads: list[threading.Thread] = []
        self._all_codes: list[str] = []
        self._core_codes: list[str] = CORE_TICKERS

        self._last_full_scan_at: datetime | None = None
        self._scan_count = 0

    def start_background_scan(self):
        if self._is_running:
            return

        self._is_running = True
        t_core = threading.Thread(target=self._core_scan_loop, daemon=True)
        t_rot = threading.Thread(target=self._market_rotation_loop, daemon=True)
        t_core.start()
        t_rot.start()
        self._threads = [t_core, t_rot]

        logger.info("Background priority scanning system activated.")

    def get_status(self) -> ScannerStatusDTO:
        """Returns structured status of the scanner."""
        return ScannerStatusDTO(
            is_running=self._is_running,
            scan_count=self._scan_count,
            last_full_scan_at=self._last_full_scan_at,
            core_codes_count=len(self._core_codes),
            is_trading_time=is_trading_time_cn()
        )

    def stop_background_scan(self, join_timeout: float = 5.0) -> None:
        """供测试与优雅停机；将 ``_is_running`` 置 False 并尝试 join 工作线程。"""
        self._is_running = False
        threads = list(self._threads)
        self._threads = []
        per = max(join_timeout / max(len(threads), 1), 0.05)
        for t in threads:
            t.join(timeout=per)

    def _core_scan_loop(self):
        """核心池扫描：高频更新 (2分钟一次)"""
        while self._is_running:
            if not is_trading_time_cn():
                time.sleep(300)
                continue

            try:
                self.process_quote_batch(self._core_codes)
                logger.debug(f"Core pool sync completed ({len(self._core_codes)} stocks)")
                time.sleep(120)
            except Exception as e:
                logger.error(f"Core scan loop error: {e}", exc_info=True)
                time.sleep(30)

    def _market_rotation_loop(self):
        """全市场轮询：分批抓取 (20分钟一轮)"""
        while self._is_running:
            try:
                rotation_pool = self.get_rotation_symbols()

                if not rotation_pool:
                    time.sleep(60)
                    continue

                batch_size = 60
                for i in range(0, len(rotation_pool), batch_size):
                    if not self._is_running: break
                    batch = rotation_pool[i : i + batch_size]
                    self.process_quote_batch(batch)
                    time.sleep(1.0)

                self._last_full_scan_at = datetime.now()
                self._scan_count += 1
                self.refresh_market_sentiment()

                logger.info(f"Full market rotation #{self._scan_count} finished at {self._last_full_scan_at.strftime('%H:%M:%S')}")

                wait = 900 if is_trading_time_cn() else 3600
                time.sleep(wait)

            except Exception as e:
                logger.error(f"Rotation scan loop error: {e}", exc_info=True)
                time.sleep(60)

    def get_rotation_symbols(self) -> list[str]:
        """Get symbols excluding core tickers."""
        all_codes = self._discover_all_codes()
        return [c for c in all_codes if c not in self._core_codes]

    def process_quote_batch(self, symbols: list[str]):
        """Process a single batch of symbols (fetch and update sentiment)."""
        self._provider.get_realtime_quotes(symbols)
        self.refresh_market_sentiment()

    def refresh_market_sentiment(self):
        try:
            stocks = self._cache.get_all_stocks(max_age_minutes=15)  # 只用15分钟内的新数据
            if not stocks: return

            up = len([s for s in stocks if float(s.get('change_pct', 0)) > 0])
            down = len([s for s in stocks if float(s.get('change_pct', 0)) < 0])
            flat = len(stocks) - up - down

            self._cache.save_sentiment("CN", up, down, flat)
            try:
                from app.core.shanghai_time import today_sh_str
                self._cache.save_sentiment_daily("CN", today_sh_str(), up, down, flat)
            except Exception as e:
                logger.warning("scanner_service.py.refresh_market_sentiment: %s", e)

            # Publish event instead of direct calls
            try:
                from app.application.events.event_bus import publish_event, EventType
                publish_event(
                    EventType.DATA_SYNCED,
                    payload={"market": "CN", "up": up, "down": down, "flat": flat, "total": len(stocks)},
                    source="ScannerService"
                )
            except Exception as e:
                logger.warning("scanner_service.py.refresh_market_sentiment: %s", e)
        except Exception as e:
            logger.warning(f"Failed to refresh market sentiment: {e}")

    def _discover_all_codes(self) -> list[str]:
        try:
            import akshare as ak
            import io
            import contextlib
            sink = io.StringIO()
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                codes = df['代码'].astype(str).tolist()
                return [c[-6:] for c in codes]
        except Exception as e:
            logger.warning(f"Stock discovery failed, using core seeds: {e}")
        return self._core_codes

    def run_core_scan_once(self) -> ScanResultDTO:
        """核心池一次拉取（供 Celery / 手动调用）；非交易时段跳过。"""
        if not is_trading_time_cn():
            return ScanResultDTO(
                ok=True,
                skipped=True,
                reason="off_trading_hours",
                codes_count=len(self._core_codes)
            )
        try:
            self.process_quote_batch(self._core_codes)
            return ScanResultDTO(ok=True, codes_count=len(self._core_codes))
        except Exception as exc:
            logger.exception("run_core_scan_once failed")
            return ScanResultDTO(ok=False, error=str(exc), codes_count=len(self._core_codes))

    def run_full_rotation_once(self) -> ScanResultDTO:
        """全市场分批轮询一轮（同步执行，适合非分布式或调试）。"""
        try:
            rotation_pool = self.get_rotation_symbols()
            if not rotation_pool:
                self.refresh_market_sentiment()
                return ScanResultDTO(ok=True, reason="empty_rotation")

            batch_size = 60
            for i in range(0, len(rotation_pool), batch_size):
                batch = rotation_pool[i : i + batch_size]
                self.process_quote_batch(batch)
                time.sleep(1.0)

            self._last_full_scan_at = datetime.now()
            self._scan_count += 1

            return ScanResultDTO(
                ok=True,
                codes_count=len(rotation_pool),
                scan_count=self._scan_count
            )
        except Exception as exc:
            logger.exception("run_full_rotation_once failed")
            return ScanResultDTO(ok=False, error=str(exc))
