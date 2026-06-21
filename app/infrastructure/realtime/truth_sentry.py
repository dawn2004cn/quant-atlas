from __future__ import annotations
"""TruthSentry — real-time multi-source data reconciliation on EventBus."""

from typing import Any

from app.core.event_bus import (
    AnalysisStaleEvent,
    MarketDataUpdatedEvent,
    TruthDeviationEvent,
    get_event_bus,
)
from app.core.logger import get_logger
from app.domain.ports.data_quality_ports import DataQualityPort
from app.domain.verification import mark_pending

logger = get_logger(__name__)

_started = False


class TruthSentry:
    """Subscribe to market updates; publish truth deviation + stale analysis events."""

    def __init__(
        self,
        data_quality: DataQualityPort,
        *,
        diff_threshold_pct: float = 0.5,
    ) -> None:
        self._data_quality = data_quality
        self._threshold = diff_threshold_pct

    def start(self) -> None:
        """Register EventBus handlers (idempotent)."""
        global _started
        if _started:
            return
        bus = get_event_bus()
        bus.subscribe(MarketDataUpdatedEvent, self._on_market_update, priority=50)
        _started = True
        logger.info("TruthSentry started (threshold=%.2f%%)", self._threshold)

    def check_symbol(self, symbol: str, market: str = "CN") -> list[TruthDeviationEvent]:
        """Synchronous reconciliation for one symbol (API / tests)."""
        published: list[TruthDeviationEvent] = []
        comparisons = self._data_quality.compare_sources(symbol, market)
        for comp in comparisons:
            if not comp.anomaly or comp.field != "close_price":
                continue
            evt = TruthDeviationEvent(
                source="TruthSentry",
                symbol=symbol,
                market=market,
                field=comp.field,
                source_a=comp.source_a,
                source_b=comp.source_b,
                value_a=comp.value_a,
                value_b=comp.value_b,
                diff_pct=comp.diff_pct,
                threshold_pct=self._threshold,
            )
            self._emit_deviation(evt)
            published.append(evt)
        return published

    def _on_market_update(self, event: MarketDataUpdatedEvent) -> None:
        symbol = (event.symbol or "").strip().upper()
        if not symbol:
            return
        market = (event.market or "CN").strip().upper()
        self.check_symbol(symbol, market)

    def _emit_deviation(self, evt: TruthDeviationEvent) -> None:
        bus = get_event_bus()
        bus.publish(evt)
        reason = (
            f"{evt.source_a} vs {evt.source_b} 收盘价偏差 "
            f"{evt.diff_pct:.3f}% (阈值 {evt.threshold_pct}%)"
        )
        mark_pending(evt.symbol, evt.market, reason=reason)
        try:
            from app.infrastructure.replay.evidence_replay_store import append_snapshot

            append_snapshot(
                evt.symbol,
                evt.market,
                event_type="TruthDeviationEvent",
                payload={
                    "field": evt.field,
                    "diff_pct": evt.diff_pct,
                    "source_a": evt.source_a,
                    "source_b": evt.source_b,
                    "reason": reason,
                },
                source="TruthSentry",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("truth replay snapshot skipped: %s", exc)
        bus.publish(
            AnalysisStaleEvent(
                source="TruthSentry",
                symbol=evt.symbol,
                market=evt.market,
                reason=reason,
                trigger_event=evt.__class__.__name__,
            )
        )
        logger.warning("TruthSentry deviation sym=%s %s", evt.symbol, reason)


def start_truth_sentry(data_quality: DataQualityPort | None = None) -> TruthSentry | None:
    """Bootstrap helper: wire TruthSentry with UnifiedDataTruth."""
    if data_quality is None:
        try:
            from app.infrastructure.adapters.data_quality_port_adapter import (
                DataQualityPortAdapter,
            )

            data_quality = DataQualityPortAdapter()
        except Exception as exc:  # noqa: BLE001
            logger.warning("TruthSentry skipped: %s", exc)
            return None
    sentry = TruthSentry(data_quality)
    sentry.start()
    return sentry
