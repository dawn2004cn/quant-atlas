from __future__ import annotations

from app.domain.data_truth.byzantine_consensus import SourceQuote, compute_quorum_consensus


def test_quorum_all_sources_agree() -> None:
    result = compute_quorum_consensus(
        "600519",
        [
            SourceQuote("TDX", 100.0),
            SourceQuote("Qlib", 100.1),
            SourceQuote("AkShare", 99.9),
        ],
        threshold_pct=0.5,
    )
    assert result.consensus_value is not None
    assert result.byzantine_fault is False
    assert result.confidence >= 0.9
    assert len(result.outlier_sources) == 0


def test_quorum_flags_single_byzantine_outlier() -> None:
    result = compute_quorum_consensus(
        "600519",
        [
            SourceQuote("TDX", 100.0),
            SourceQuote("Qlib", 100.2),
            SourceQuote("AkShare", 105.0),
        ],
        threshold_pct=0.5,
    )
    assert result.byzantine_fault is True
    assert "AkShare" in result.outlier_sources
    assert result.consensus_value is not None
    assert len(result.agreeing_sources) >= 2


def test_quorum_insufficient_sources() -> None:
    result = compute_quorum_consensus(
        "600519",
        [SourceQuote("TDX", 100.0)],
        min_sources=2,
    )
    assert result.consensus_value is None
    assert result.confidence < 0.5
