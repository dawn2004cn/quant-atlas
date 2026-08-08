"""Unit tests for shadow account journal analysis service."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.modules.ai_agent.services.shadow_account_analysis_service import analyze_upload
from werkzeug.datastructures import FileStorage


def _journal_csv() -> str:
    rows = [
        "datetime,symbol,side,quantity,price,fee",
        "2024-01-02 10:00:00,600519.SH,buy,100,1800,5",
        "2024-01-10 14:00:00,600519.SH,sell,100,1900,5",
        "2024-01-03 10:00:00,000001.SZ,buy,200,10,2",
        "2024-01-12 14:00:00,000001.SZ,sell,200,9.5,2",
    ]
    return "\n".join(rows)


def test_analyze_upload_returns_metrics():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(_journal_csv())
        path = Path(tmp.name)

    try:
        with path.open("rb") as fh:
            upload = FileStorage(stream=fh, filename="trades.csv", content_type="text/csv")
            result = analyze_upload("user-test", upload)
    finally:
        path.unlink(missing_ok=True)

    assert result["total_trades"] == 2
    assert 0.0 <= result["win_rate"] <= 1.0
    assert "summary" in result


def test_analyze_upload_rejects_missing_file():
    with pytest.raises(ValueError, match="file_required"):
        analyze_upload("user-test", None)  # type: ignore[arg-type]
