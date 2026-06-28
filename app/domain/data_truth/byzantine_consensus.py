from __future__ import annotations

"""Byzantine-style quorum consensus over multi-source market quotes."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceQuote:
    """Single-source observation for quorum reconciliation."""

    source: str
    value: float
    trade_date: str = ""


@dataclass(frozen=True)
class QuorumConsensusResult:
    """Quorum outcome with outlier attribution."""

    symbol: str
    field: str
    consensus_value: float | None
    source_count: int
    quorum_required: int
    agreeing_sources: list[str] = field(default_factory=list)
    outlier_sources: list[str] = field(default_factory=list)
    source_deviations: list[dict[str, Any]] = field(default_factory=list)
    byzantine_fault: bool = False
    confidence: float = 0.0
    evidence: str = ""


def compute_quorum_consensus(
    symbol: str,
    quotes: list[SourceQuote],
    *,
    field: str = "close_price",
    threshold_pct: float = 0.5,
    min_sources: int = 2,
) -> QuorumConsensusResult:
    """Median-based quorum; sources beyond ``threshold_pct`` from median are outliers."""
    valid = [q for q in quotes if q.value > 0 and (q.source or "").strip()]
    if len(valid) < min_sources:
        return QuorumConsensusResult(
            symbol=symbol,
            field=field,
            consensus_value=None,
            source_count=len(valid),
            quorum_required=max(1, (min_sources // 2) + 1),
            confidence=0.35,
            evidence=f"可用数据源不足（{len(valid)}/{min_sources}）",
        )

    values = sorted(q.value for q in valid)
    mid = len(values) // 2
    if len(values) % 2 == 1:
        consensus = values[mid]
    else:
        consensus = (values[mid - 1] + values[mid]) / 2.0

    deviations: list[dict[str, Any]] = []
    outliers: list[str] = []
    agreeing: list[str] = []
    for quote in valid:
        diff_pct = abs(quote.value - consensus) / consensus * 100.0 if consensus > 0 else 0.0
        row = {
            "source": quote.source,
            "value": quote.value,
            "trade_date": quote.trade_date,
            "diff_pct": round(diff_pct, 4),
        }
        deviations.append(row)
        if diff_pct > threshold_pct:
            outliers.append(quote.source)
        else:
            agreeing.append(quote.source)

    quorum_required = (len(valid) // 2) + 1
    has_quorum = len(agreeing) >= quorum_required
    byzantine_fault = bool(outliers)
    if not outliers:
        confidence = 0.95
        evidence = f"{len(valid)} 源一致，中位数共识 {consensus:.4f}"
    elif has_quorum:
        confidence = 0.78
        evidence = (
            f"拜占庭异常：{', '.join(outliers)} 偏离中位数 {consensus:.4f} "
            f"> {threshold_pct}%"
        )
    else:
        confidence = 0.42
        evidence = f"未达法定多数（{len(agreeing)}/{quorum_required}），共识不可信"

    return QuorumConsensusResult(
        symbol=symbol,
        field=field,
        consensus_value=round(consensus, 6),
        source_count=len(valid),
        quorum_required=quorum_required,
        agreeing_sources=agreeing,
        outlier_sources=outliers,
        source_deviations=deviations,
        byzantine_fault=byzantine_fault,
        confidence=confidence,
        evidence=evidence,
    )


__all__ = ["SourceQuote", "QuorumConsensusResult", "compute_quorum_consensus"]
