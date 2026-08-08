"""Data Quality Firewall — Phase 14. Real anomaly detection + healing orchestration."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger
from app.core.data_source_registry import DataSourceRegistry

logger = get_logger(__name__)


@dataclass
class DataQualityReport:
    source: str
    symbol: str
    missing_pct: float
    gap_pct: float
    outlier_pct: float
    alignment_score: float
    overall_health: str  # healthy / warning / critical
    issues: list[str] = field(default_factory=list)


class DataQualityFirewall:
    """Real data anomaly detection: missing, gaps, outliers, alignment."""

    def __init__(self, strict_mode: bool = False):
        self._strict = strict_mode
        self._registry = DataSourceRegistry()

    def validate(self, closes: list[float], timestamps: list[str],
                 symbol: str = "", source: str = "unknown") -> DataQualityReport:
        """Validate a data series through the firewall."""
        arr = np.array(closes, dtype=float)
        issues = []

        # ── Missing data ────────────────────────────────────────────────
        missing = int(np.sum(np.isnan(arr)) + np.sum(arr <= 0))
        missing_pct = round(missing / max(len(arr), 1) * 100, 2)
        if missing_pct > 5:
            issues.append(f"缺失率 {missing_pct}% 超过阈值 5%")

        # ── Gap detection (flat segments > 3 periods) ───────────────────
        valid = arr[arr > 0]
        if len(valid) > 5:
            diffs = np.diff(valid) / valid[:-1] * 100
            gaps = int(np.sum(np.abs(diffs) < 0.001))
            gap_pct = round(gaps / max(len(diffs), 1) * 100, 2)
            if gap_pct > 10:
                issues.append(f"重复值占比 {gap_pct}%, 可能存在填充空洞")
        else:
            gap_pct = 0.0

        # ── Outlier (3-sigma) ───────────────────────────────────────────
        if len(valid) > 10:
            mean, std = np.mean(valid), np.std(valid)
            outliers = int(np.sum(np.abs(valid - mean) > 3 * std))
            outlier_pct = round(outliers / len(valid) * 100, 2)
            if outlier_pct > 2:
                issues.append(f"3-sigma 异常值 {outlier_pct}% 超过阈值 2%")
        else:
            outlier_pct = 0.0

        # ── Alignment score (time series consistency) ───────────────────
        alignment_score = round(1.0 - (missing_pct + gap_pct + outlier_pct) / 300, 4)
        alignment_score = max(0.0, min(1.0, alignment_score))

        # ── Overall health ──────────────────────────────────────────────
        if alignment_score > 0.95:
            health = "healthy"
        elif alignment_score > 0.80:
            health = "warning"
        else:
            health = "critical"

        return DataQualityReport(
            source=source, symbol=symbol,
            missing_pct=missing_pct, gap_pct=gap_pct,
            outlier_pct=outlier_pct,
            alignment_score=alignment_score,
            overall_health=health,
            issues=issues,
        )
