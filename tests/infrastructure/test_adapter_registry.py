"""Execution adapter registry status."""

from app.infrastructure.execution.adapter_registry import list_execution_adapters


def test_list_execution_adapters_includes_qmt_and_p2():
    rows = list_execution_adapters()
    ids = {r["adapter_id"] for r in rows}
    assert "qmt" in ids
    assert "ccxt" in ids
    assert "ibkr" in ids
    assert "ctp" in ids
    qmt = next(r for r in rows if r["adapter_id"] == "qmt")
    assert "ready" in qmt
    ibkr = next(r for r in rows if r["adapter_id"] == "ibkr")
    assert ibkr["ready"] is False
    assert ibkr["phase"] == "P2"
