"""QFQ/HFQ adjustment helpers."""

from __future__ import annotations

from app.infrastructure.tdx_local.qfq_calculator import apply_hfq_to_rows, apply_qfq_to_rows


def test_apply_qfq_and_hfq_differ_on_history() -> None:
    rows = [
        {"date": "2020-01-02", "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 100, "amount": 1000},
        {"date": "2020-06-01", "open": 20.0, "high": 21.0, "low": 19.0, "close": 20.0, "volume": 100, "amount": 2000},
    ]
    factors = [
        {"date": "2020-01-02", "factor": 0.5},
        {"date": "2020-06-01", "factor": 1.0},
    ]
    qfq = apply_qfq_to_rows(rows, factors)
    hfq = apply_hfq_to_rows(rows, factors)
    assert qfq[-1]["close"] == 20.0
    assert hfq[0]["close"] == 10.0
    assert hfq[-1]["close"] == 40.0
