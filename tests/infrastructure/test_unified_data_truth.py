from __future__ import annotations

from unittest.mock import patch

from app.infrastructure.data_truth.unified_data_truth import UnifiedDataTruth


def test_compare_sources_flags_anomaly() -> None:
    truth = UnifiedDataTruth(close_diff_threshold_pct=0.5)
    with (
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_tdx_bar",
            return_value={"date": "2026-06-04", "close": 100.0},
        ),
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_qlib_bar",
            return_value={"date": "2026-06-04", "close": 101.0},
        ),
    ):
        comps = truth.compare_sources("600519", "CN")
    assert len(comps) == 1
    assert comps[0].anomaly is True
    assert comps[0].diff_pct == 1.0


def test_compare_sources_ok_when_aligned() -> None:
    truth = UnifiedDataTruth(close_diff_threshold_pct=0.5)
    with (
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_tdx_bar",
            return_value={"date": "2026-06-04", "close": 100.0},
        ),
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_qlib_bar",
            return_value={"date": "2026-06-04", "close": 100.2},
        ),
    ):
        comps = truth.compare_sources("600519", "CN")
    assert comps[0].anomaly is False


def test_quorum_consensus_flags_byzantine_outlier() -> None:
    truth = UnifiedDataTruth(close_diff_threshold_pct=0.5)
    with (
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_tdx_bar",
            return_value={"date": "2026-06-04", "close": 100.0},
        ),
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_qlib_bar",
            return_value={"date": "2026-06-04", "close": 100.1},
        ),
        patch(
            "app.infrastructure.data_truth.unified_data_truth.latest_akshare_bar",
            return_value={"date": "2026-06-04", "close": 106.0},
        ),
    ):
        result = truth.quorum_consensus("600519", "CN")
    assert result.byzantine_fault is True
    assert "AkShare" in result.outlier_sources
    assert result.consensus_value is not None
