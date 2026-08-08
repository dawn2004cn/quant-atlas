"""Tdx Qlib CSV writer unit tests."""

from __future__ import annotations

from pathlib import Path

from app.modules.data.services.tdx_dayk_csv_writer import write_qlib_csv


def test_write_qlib_csv_creates_file(tmp_path: Path) -> None:
    rows = [
        {
            "date": "2024-01-01",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000,
            "amount": 10500,
        }
    ]
    count, min_date, max_date = write_qlib_csv(tmp_path, "SH600519", rows)
    assert count == 1
    assert min_date == "2024-01-01"
    assert max_date == "2024-01-01"
    csv_path = tmp_path / "SH600519.csv"
    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "2024-01-01" in content


def test_write_qlib_csv_merge(tmp_path: Path) -> None:
    first = [
        {
            "date": "2024-01-01",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000,
            "amount": 10500,
        }
    ]
    write_qlib_csv(tmp_path, "SH600519", first)
    second = [
        {
            "date": "2024-01-02",
            "open": 10.5,
            "high": 11.5,
            "low": 10.0,
            "close": 11.0,
            "volume": 900,
            "amount": 9900,
        }
    ]
    count, _, _ = write_qlib_csv(tmp_path, "SH600519", second, merge=True)
    assert count == 2
