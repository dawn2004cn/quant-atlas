import time

from app.application.services.scanner_service import ScannerApplicationService


class _DummyMarketProvider:
    def get_realtime_quotes(self, symbols=None, market=None):
        return []


class _TestScanner(ScannerApplicationService):
    """避免真实轮询与 AkShare 发现，仅验证线程生命周期。"""

    def _core_scan_loop(self):
        while self._is_running:
            time.sleep(0.01)

    def _market_rotation_loop(self):
        while self._is_running:
            time.sleep(0.01)


def test_scanner_start_is_idempotent_and_stop_works():
    scanner = _TestScanner(_DummyMarketProvider())
    scanner.start_background_scan()
    threads_ref = scanner._threads
    assert len(threads_ref) == 2
    scanner.start_background_scan()
    assert scanner._threads is threads_ref
    assert scanner.is_running()
    scanner.stop_background_scan(join_timeout=0.5)
    assert not scanner.is_running()
