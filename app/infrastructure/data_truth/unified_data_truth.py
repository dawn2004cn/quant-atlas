from __future__ import annotations
"""UnifiedDataTruth — reconcile TDX vs Qlib close prices."""

from typing import Any

from app.core.logger import get_logger
from app.domain.ports.data_quality_ports import (
    DataQualityAlert,
    DataQualityPort,
    DataQualityReport,
    SourceComparison,
)
from app.domain.data_truth.byzantine_consensus import (
    QuorumConsensusResult,
    SourceQuote,
    compute_quorum_consensus,
)
from app.infrastructure.data_truth.bar_readers import (
    latest_akshare_bar,
    latest_qlib_bar,
    latest_tdx_bar,
)

logger = get_logger(__name__)

DEFAULT_CLOSE_DIFF_THRESHOLD_PCT = 0.5


class UnifiedDataTruth(DataQualityPort):
    """Compare TDX lday and qlib_bin; TDX is canonical on conflict."""

    def __init__(
        self,
        *,
        tdx_root: str | None = None,
        close_diff_threshold_pct: float = DEFAULT_CLOSE_DIFF_THRESHOLD_PCT,
    ) -> None:
        self._tdx_root = tdx_root
        self._threshold = close_diff_threshold_pct

    def check_completeness(self, symbol: str, market: str, days: int = 30) -> DataQualityReport:
        alerts: list[DataQualityAlert] = []
        tdx = latest_tdx_bar(symbol, tdx_root=self._tdx_root)
        qlib = latest_qlib_bar(symbol)
        sources_ok = int(tdx is not None) + int(qlib is not None)
        completeness = sources_ok / 2.0
        if tdx is None:
            alerts.append(
                DataQualityAlert(
                    severity="warning",
                    symbol=symbol,
                    field="tdx_bars",
                    expected=">=1 bar",
                    actual=0,
                    message="TDX lday 无数据",
                    source="TDX",
                )
            )
        if qlib is None:
            alerts.append(
                DataQualityAlert(
                    severity="warning",
                    symbol=symbol,
                    field="qlib_bars",
                    expected=">=1 bar",
                    actual=0,
                    message="qlib_bin 无数据",
                    source="Qlib",
                )
            )
        return DataQualityReport(
            total_checks=2,
            passed=sources_ok,
            failed=2 - sources_ok,
            alerts=alerts,
            coverage=completeness,
            completeness=completeness,
        )

    def detect_anomalies(self, symbol: str, market: str) -> list[DataQualityAlert]:
        alerts: list[DataQualityAlert] = []
        for comp in self.compare_sources(symbol, market):
            if comp.anomaly and comp.diff_pct is not None:
                alerts.append(
                    DataQualityAlert(
                        severity="critical",
                        symbol=symbol,
                        field=comp.field,
                        expected=f"<{self._threshold}% diff",
                        actual=f"{comp.diff_pct:.3f}%",
                        message=(
                            f"{comp.source_a} vs {comp.source_b} "
                            f"偏差 {comp.diff_pct:.3f}% (date alignment)"
                        ),
                        source=f"{comp.source_a}/{comp.source_b}",
                    )
                )
        return alerts

    def compare_sources(self, symbol: str, market: str) -> list[SourceComparison]:
        comparisons: list[SourceComparison] = []
        tdx = latest_tdx_bar(symbol, tdx_root=self._tdx_root)
        qlib = latest_qlib_bar(symbol)
        if not tdx or not qlib:
            return comparisons

        tdx_close = float(tdx.get("close") or 0)
        qlib_close = float(qlib.get("close") or 0)
        if tdx_close <= 0 or qlib_close <= 0:
            return comparisons

        diff_pct = abs(tdx_close - qlib_close) / tdx_close * 100.0
        same_date = (tdx.get("date") or "") == (qlib.get("date") or "")
        anomaly = diff_pct > self._threshold

        comparisons.append(
            SourceComparison(
                symbol=symbol,
                field="close_price",
                source_a="TDX",
                source_b="Qlib",
                value_a=tdx_close,
                value_b=qlib_close,
                diff_pct=round(diff_pct, 4),
                anomaly=anomaly,
            )
        )
        if not same_date:
            comparisons.append(
                SourceComparison(
                    symbol=symbol,
                    field="trade_date",
                    source_a="TDX",
                    source_b="Qlib",
                    value_a=None,
                    value_b=None,
                    diff_pct=None,
                    anomaly=True,
                )
            )
            logger.debug(
                "UnifiedDataTruth date mismatch sym=%s tdx=%s qlib=%s",
                symbol,
                tdx.get("date"),
                qlib.get("date"),
            )
        return comparisons

    def check_adjustment_factors(self, symbol: str, market: str) -> list[DataQualityAlert]:
        return []

    def quorum_consensus(self, symbol: str, market: str = "CN") -> QuorumConsensusResult:
        """Three-source median quorum (TDX / Qlib / AkShare) with Byzantine outlier tagging."""
        quotes: list[SourceQuote] = []
        tdx = latest_tdx_bar(symbol, tdx_root=self._tdx_root)
        if tdx and float(tdx.get("close") or 0) > 0:
            quotes.append(
                SourceQuote(
                    source="TDX",
                    value=float(tdx["close"]),
                    trade_date=str(tdx.get("date") or ""),
                )
            )
        qlib = latest_qlib_bar(symbol)
        if qlib and float(qlib.get("close") or 0) > 0:
            quotes.append(
                SourceQuote(
                    source="Qlib",
                    value=float(qlib["close"]),
                    trade_date=str(qlib.get("date") or ""),
                )
            )
        ak = latest_akshare_bar(symbol)
        if ak and float(ak.get("close") or 0) > 0:
            quotes.append(
                SourceQuote(
                    source="AkShare",
                    value=float(ak["close"]),
                    trade_date=str(ak.get("date") or ""),
                )
            )
        return compute_quorum_consensus(
            symbol,
            quotes,
            threshold_pct=self._threshold,
            min_sources=2,
        )
