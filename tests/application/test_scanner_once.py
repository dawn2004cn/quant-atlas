"""Scanner 单次执行（Celery / 手动）逻辑。"""

from __future__ import annotations

from app.application.services.scanner_service import ScannerApplicationService


class _DummyMarketProvider:
    def get_realtime_quotes(self, symbols=None, market=None):
        return []


def test_run_core_scan_once_skipped_off_hours(monkeypatch):
    scanner = ScannerApplicationService(_DummyMarketProvider())
    monkeypatch.setattr(scanner, "_is_trading_time", lambda: False)
    r = scanner.run_core_scan_once()
    assert r["ok"] is True
    assert r.get("skipped") is True
    assert r.get("reason") == "off_trading_hours"


def test_run_core_scan_once_trading(monkeypatch):
    scanner = ScannerApplicationService(_DummyMarketProvider())
    monkeypatch.setattr(scanner, "_is_trading_time", lambda: True)
    r = scanner.run_core_scan_once()
    assert r["ok"] is True
    assert r.get("skipped") is False
    assert r.get("core_codes") == len(scanner._core_codes)


def test_run_full_rotation_once_with_rotation_pool(monkeypatch):
    scanner = ScannerApplicationService(_DummyMarketProvider())
    monkeypatch.setattr(scanner, "_discover_all_codes", lambda: ["700001", "700002"])
    r = scanner.run_full_rotation_once()
    assert r["ok"] is True
    assert r.get("batches") == 1
    assert r.get("rotation_codes") == 2
    assert r.get("scan_count") == 1
