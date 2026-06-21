"""本地 lday 与 qfq 合并逻辑（不请求网络）。"""

from app.infrastructure.qlib.cn_ohlcv_merge import _merge_prefix_local_with_qfq


def test_merge_scales_local_prefix_to_qfq_overlap():
    local = [
        {"date": "2023-12-28", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
        {"date": "2024-01-02", "open": 10.2, "high": 10.4, "low": 10.0, "close": 10.3, "volume": 900},
    ]
    qfq = [
        {"date": "2024-01-02", "open": 20.4, "high": 20.8, "low": 20.0, "close": 20.6, "volume": 900},
        {"date": "2024-01-03", "open": 20.6, "high": 21.0, "low": 20.5, "close": 20.9, "volume": 800},
    ]
    out = _merge_prefix_local_with_qfq(local, qfq)
    dates = [r["date"] for r in out]
    assert "2023-12-28" in dates
    assert "2024-01-02" in dates and "2024-01-03" in dates
    dec = next(r for r in out if r["date"] == "2023-12-28")
    assert abs(dec["close"] - 20.4) < 0.01
