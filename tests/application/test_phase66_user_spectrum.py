"""Phase 66: User spectrum tiers, audit hash chain, tick stream."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.portfolio_risk.services.fund_tier_service import AuditTrailService
from app.modules.market_data.services.tick_stream_service import stream_status


def test_audit_hash_chain_intact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "audit_trail.jsonl"
    svc = AuditTrailService()
    monkeypatch.setattr(svc, "_store", store)

    s1 = svc.record_snapshot("ord.001", 1, "600519", "buy", 100, 1500.0)
    s2 = svc.record_snapshot("ord.001", 1, "600519", "buy", 50, 1500.0)
    assert s1.chain_hash
    assert s2.previous_hash == s1.chain_hash

    verify = svc.verify_order_chain("ord.001")
    assert verify.valid is True
    assert verify.snapshot_count == 2

    global_verify = svc.verify_global_chain()
    assert global_verify.valid is True
    assert global_verify.snapshot_count == 2


def test_audit_tamper_detection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "audit_trail.jsonl"
    svc = AuditTrailService()
    monkeypatch.setattr(svc, "_store", store)
    svc.record_snapshot("ord.tamper", 1, "000001", "sell", 200, 10.0)

    raw = store.read_text(encoding="utf-8").replace('"price": 10.0', '"price": 9.99')
    store.write_text(raw, encoding="utf-8")

    verify = svc.verify_order_chain("ord.tamper")
    assert verify.valid is False


def test_tick_stream_status_defaults() -> None:
    status = stream_status()
    assert "enabled" in status
    assert "interval_sec" in status
    assert "global_subscribers" in status


def test_boutique_factor_mining_service() -> None:
    from app.modules.strategy.services.alpha_mining_service import AutoAlphaMiningService

    svc = AutoAlphaMiningService()
    svc.seed_population(size=10)
    svc.evolve(fitness_fn=lambda e: len(e) * 0.01, population_size=10)
    top = svc.get_top_factors(3)
    assert len(top) <= 3
