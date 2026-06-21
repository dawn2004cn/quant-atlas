from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.modules.system.services.system.data_truth_guardian_service import DataTruthGuardianService
from app.core.event_bus import TruthDeviationEvent
from app.domain.data_truth.byzantine_consensus import QuorumConsensusResult
from app.domain.data_truth.guardian_schema import GuardianQuorumRequest, GuardianScanRequest
from app.domain.verification import clear_pending, list_pending, mark_pending
from app.infrastructure.realtime.truth_sentry import TruthSentry


@pytest.fixture
def guardian(tmp_path: Path) -> DataTruthGuardianService:
    quality = MagicMock()
    comp = MagicMock()
    comp.anomaly = True
    comp.field = "close_price"
    comp.source_a = "TDX"
    comp.source_b = "Qlib"
    comp.value_a = 100.0
    comp.value_b = 101.2
    comp.diff_pct = 1.2
    quality.compare_sources.return_value = [comp]
    sentry = TruthSentry(quality, diff_threshold_pct=0.5)
    dispatcher = MagicMock()
    dispatcher.dispatch.return_value = "task-abc"
    return DataTruthGuardianService(
        data_quality=quality,
        truth_sentry=sentry,
        task_dispatcher=dispatcher,
        store_path=tmp_path / "heal.jsonl",
    )


def test_guardian_scan_detects_deviation(guardian: DataTruthGuardianService) -> None:
    out = guardian.scan(GuardianScanRequest(symbols=["600519"], market="CN"))
    assert out["ok"] is True
    assert out["deviation_count"] == 1
    assert out["deviations"][0]["symbol"] == "600519"


def test_guardian_heal_clear_pending(guardian: DataTruthGuardianService) -> None:
    mark_pending("600519", "CN", reason="test")
    assert "CN:600519" in list_pending()
    out = guardian.heal(symbol="600519", market="CN", action="clear_pending")
    assert out["ok"] is True
    assert out["action"]["dispatched"] is True
    clear_pending("600519", "CN")


def test_guardian_quorum_scan(guardian: DataTruthGuardianService) -> None:
    quality = guardian._quality
    quality.quorum_consensus.return_value = QuorumConsensusResult(
        symbol="600519",
        field="close_price",
        consensus_value=1800.0,
        source_count=3,
        quorum_required=2,
        agreeing_sources=["TDX", "Qlib"],
        outlier_sources=["AkShare"],
        source_deviations=[{"source": "AkShare", "diff_pct": 1.1}],
        byzantine_fault=True,
        confidence=0.78,
        evidence="test quorum",
    )
    out = guardian.quorum_scan(GuardianQuorumRequest(symbols=["600519"], market="CN"))
    assert out["ok"] is True
    assert out["byzantine_fault_count"] == 1
    assert out["quorum_results"][0]["outlier_sources"] == ["AkShare"]


def test_guardian_manifest() -> None:
    svc = DataTruthGuardianService(data_quality=MagicMock(), truth_sentry=MagicMock())
    m = svc.get_manifest()
    assert m["ok"] is True
    assert "resync_qlib" in m["heal_actions"]
