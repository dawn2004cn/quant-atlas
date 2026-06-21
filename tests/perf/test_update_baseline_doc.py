"""Tests for perf baseline doc updater."""

from __future__ import annotations

from scripts.perf.update_baseline_doc import build_table_rows, patch_markdown

SAMPLE_REPORT = {
    "endpoints": [
        {
            "name": "system_health",
            "path": "/system/health",
            "p50_ms": 12.5,
            "p95_ms": 20.0,
            "p99_ms": 25.0,
            "error_rate": 0.0,
        },
        {
            "name": "market_quotes",
            "path": "/api/v1/markets/CN/quotes?symbol=600519&limit=1",
            "p50_ms": 80.0,
            "p95_ms": 120.0,
            "p99_ms": 150.0,
            "error_rate": 0.01,
        },
    ],
    "decision": {"async_optimization_recommended": False, "reason": "ok"},
}

SAMPLE_DOC = """## 记录模板

| 端点 | P50 (ms) | P95 (ms) | P99 (ms) | 错误率 | 日期 |
|------|----------|----------|----------|--------|------|
| `/system/health` | | | | | |

## 决策门槛
"""


def test_build_table_rows_formats_error_rate():
    rows = build_table_rows(SAMPLE_REPORT, "2026-06-15")
    assert len(rows) == 2
    assert "12.5" in rows[0]
    assert "1.00%" in rows[1]


def test_patch_markdown_replaces_table_body():
    rows = build_table_rows(SAMPLE_REPORT, "2026-06-15")
    out = patch_markdown(SAMPLE_DOC, rows)
    assert "`/system/health` | 12.5" in out
    assert "2026-06-15" in out
    assert "## 决策门槛" in out
