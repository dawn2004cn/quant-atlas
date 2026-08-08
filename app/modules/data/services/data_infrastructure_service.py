from __future__ import annotations
"""Data infrastructure application service."""


from app.modules.system.services.helpers.data_infrastructure_access import (
    create_data_lineage_tracker,
    create_default_data_quality_monitor,
)
from app.core.registry import register_service
from app.domain.ports.data_quality_ports import DataQualityPort, DataQualityReport
from app.domain.ports.websocket_ports import Subscription, WebSocketPort


@register_service(name="data_infrastructure_service")
class DataInfrastructureService:
    """Application service for data infrastructure (WebSocket, Quality)."""

    def __init__(
        self,
        data_quality: DataQualityPort | None = None,
        websocket: WebSocketPort | None = None,
    ):
        self._data_quality = data_quality or create_default_data_quality_monitor()
        self._websocket = websocket
        self._lineage_tracker = create_data_lineage_tracker()

    def check_data_quality(self, symbol: str, market: str = "CN", days: int = 30) -> DataQualityReport:
        """Run data quality checks for a symbol."""
        completeness = self._data_quality.check_completeness(symbol, market, days)
        anomalies = self._data_quality.detect_anomalies(symbol, market)
        adjustments = self._data_quality.check_adjustment_factors(symbol, market)

        all_alerts = completeness.alerts + anomalies + adjustments

        return DataQualityReport(
            total_checks=completeness.total_checks + len(anomalies) + len(adjustments),
            passed=completeness.passed,
            failed=completeness.failed + len(anomalies),
            alerts=all_alerts,
            coverage=completeness.coverage,
            completeness=completeness.completeness,
        )

    def compare_data_sources(self, symbol: str, market: str = "CN") -> list[dict]:
        """Compare data across sources."""
        comparisons = self._data_quality.compare_sources(symbol, market)
        return [
            {
                "symbol": c.symbol,
                "field": c.field,
                "source_a": c.source_a,
                "source_b": c.source_b,
                "value_a": c.value_a,
                "value_b": c.value_b,
                "diff_pct": c.diff_pct,
                "anomaly": c.anomaly,
            }
            for c in comparisons
        ]

    def connect_websocket(self) -> bool:
        """Connect to WebSocket for real-time data."""
        if self._websocket is None:
            return False
        return self._websocket.connect()

    def disconnect_websocket(self) -> None:
        """Disconnect WebSocket."""
        if self._websocket is not None:
            self._websocket.disconnect()

    def subscribe_realtime(self, symbols: list[str], channels: list[str] | None = None) -> bool:
        """Subscribe to real-time quotes."""
        if self._websocket is None or not self._websocket.is_connected():
            return False
        sub = Subscription(symbols=symbols, channels=channels or ["ticker"])
        return self._websocket.subscribe(sub)

    def is_websocket_connected(self) -> bool:
        """Check WebSocket connection status."""
        if self._websocket is None:
            return False
        return self._websocket.is_connected()

    def record_data_lineage(self, symbol: str, source: str, rows: int) -> str:
        """Record data lineage for a fetch operation."""
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        return self._lineage_tracker.record_fetch(symbol, source, timestamp, rows)

    def get_data_lineage(self, symbol: str, date: str) -> list[dict]:
        """Get data lineage for a symbol on a specific date."""
        return self._lineage_tracker.get_lineage(symbol, date)