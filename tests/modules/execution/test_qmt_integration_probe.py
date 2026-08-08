"""Automated QMT integration probe tests."""

from __future__ import annotations

from app.modules.execution.services.qmt_integration_probe import run_qmt_integration_probe


def test_qmt_integration_probe_required_checks_pass(monkeypatch, tmp_path):
    monkeypatch.setenv("QMT_LIVE_SUBMIT", "0")
    monkeypatch.setenv("RISK_GUARD_ENABLED", "1")
    monkeypatch.setenv("QMT_ORDER_PERSISTENCE", "file")
    # Point persistence at tmp by patching _persist_dir
    monkeypatch.setattr(
        "app.modules.execution.services.qmt_integration_probe._persist_dir",
        lambda: tmp_path / "qmt_orders",
    )
    report = run_qmt_integration_probe(account_id="probe_acc")
    assert report.ok is True
    by_id = {c.id: c for c in report.checks}
    assert by_id["drawdown_gate"].passed is True
    assert by_id["stop_out_gate"].passed is True
    assert by_id["order_request_sim"].passed is True
    assert by_id["executor_risk_gate"].passed is True
    assert by_id["risk_guard_singleton"].passed is True


def test_qmt_probe_fails_when_live_submit(monkeypatch):
    monkeypatch.setenv("QMT_LIVE_SUBMIT", "1")
    monkeypatch.setenv("RISK_GUARD_ENABLED", "1")
    report = run_qmt_integration_probe(account_id="probe_live")
    assert report.ok is False
    assert any(c.id == "config_simulation_default" and not c.passed for c in report.checks)
