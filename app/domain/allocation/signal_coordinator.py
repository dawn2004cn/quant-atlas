from __future__ import annotations

"""Signal Coordinator - Signal De-duplication & Cross-Validation.

This module implements from strategy_plan1.md:
- SignalClustering: Cluster similar signals from multiple strategies
- CrossValidation: Validate signals against each other
- SignalAggregation: Aggregate signals with factor source awareness

Usage:
    coordinator = SignalCoordinator()
    aggregated = coordinator.coordinate(signals, factor_mapping)
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Signal:
    """Single trading signal."""
    strategy_name: str
    symbol: str
    direction: str
    confidence: float
    timestamp: datetime
    factor_source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalCluster:
    """Cluster of related signals."""
    cluster_id: str
    symbols: list[str]
    signals: list[Signal]
    dominant_direction: str
    confidence: float
    factor_sources: list[str]
    aggregated_weight: float = 1.0


@dataclass
class AggregatedSignal:
    """Aggregated signal after coordination."""
    symbol: str
    direction: str
    confidence: float
    source_count: int
    unique_factor_count: int
    cluster_info: dict[str, Any]


class SignalClustering:
    """Cluster similar signals from multiple strategies."""

    def __init__(self, similarity_threshold: float = 0.7):
        self._threshold = similarity_threshold

    def cluster_signals(
        self,
        signals: list[Signal],
    ) -> list[SignalCluster]:
        """Cluster signals by similarity."""
        if not signals:
            return []

        symbol_groups: dict[str, list[Signal]] = {}
        for signal in signals:
            if signal.symbol not in symbol_groups:
                symbol_groups[signal.symbol] = []
            symbol_groups[signal.symbol].append(signal)

        clusters = []
        for symbol, sym_signals in symbol_groups.items():
            cluster = self._create_cluster(symbol, sym_signals)
            clusters.append(cluster)

        return clusters

    def _create_cluster(
        self,
        symbol: str,
        signals: list[Signal],
    ) -> SignalCluster:
        """Create signal cluster for a symbol."""
        import uuid

        bullish = sum(1 for s in signals if s.direction.upper() in ["BUY", "LONG", "BULLISH"])
        bearish = sum(1 for s in signals if s.direction.upper() in ["SELL", "SHORT", "BEARISH"])

        if bullish > bearish:
            direction = "BUY"
            confidence = bullish / len(signals)
        elif bearish > bullish:
            direction = "SELL"
            confidence = bearish / len(signals)
        else:
            direction = "NEUTRAL"
            confidence = 0.5

        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        factor_sources = list(set(s.factor_source for s in signals))

        return SignalCluster(
            cluster_id=str(uuid.uuid4())[:8],
            symbols=[symbol],
            signals=signals,
            dominant_direction=direction,
            confidence=confidence * avg_confidence,
            factor_sources=factor_sources,
        )


class FactorSourceNormalizer:
    """Normalize signals from same factor source."""

    def __init__(self, source_groups: dict[str, list[str]] | None = None):
        self._source_groups = source_groups or {
            "momentum": ["ma_cross", "rsi_divergence", "macd_crossover"],
            "mean_reversion": ["bollinger", "pair_trading", " oscillator"],
            "value": ["pe_ratio", "pb_ratio", "dividend_yield"],
            "quality": ["roe", "debt_ratio", "cash_flow"],
        }

    def normalize(
        self,
        signals: list[Signal],
    ) -> dict[str, list[Signal]]:
        """Group signals by factor source."""
        grouped: dict[str, list[Signal]] = {}

        for signal in signals:
            source = self._classify_source(signal)
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(signal)

        return grouped

    def _classify_source(self, signal: Signal) -> str:
        """Classify signal factor source."""
        strategy = signal.strategy_name.lower()

        for source, patterns in self._source_groups.items():
            for pattern in patterns:
                if pattern in strategy:
                    return source

        return "other"


class SignalCoordinator:
    """Complete signal coordination with de-duplication."""

    def __init__(
        self,
        clustering: SignalClustering | None = None,
        normalizer: FactorSourceNormalizer | None = None,
    ):
        self._clustering = clustering or SignalClustering()
        self._normalizer = normalizer or FactorSourceNormalizer()

    def coordinate(
        self,
        signals: list[Signal],
        factor_exposure_limit: float = 0.6,
    ) -> list[AggregatedSignal]:
        """Coordinate signals with de-duplication."""
        if not signals:
            return []

        clusters = self._clustering.cluster_signals(signals)

        source_grouped = self._normalizer.normalize(signals)

        aggregated = []

        for cluster in clusters:
            unique_sources = len(set(cluster.factor_sources))
            source_exposure = self._calculate_source_exposure(
                cluster.signals,
                source_grouped,
            )

            if source_exposure > factor_exposure_limit:
                adjusted_confidence = cluster.confidence * (1 - source_exposure)
                adjusted_weight = 1 - source_exposure
                cluster.aggregated_weight = adjusted_weight

                logger.warning(
                    f"Factor exposure {source_exposure:.2%} exceeds limit for {cluster.symbols}, "
                    f"adjusted confidence to {adjusted_confidence:.2f}"
                )
            else:
                adjusted_confidence = cluster.confidence
                adjusted_weight = 1.0

            aggregated.append(AggregatedSignal(
                symbol=cluster.symbols[0] if cluster.symbols else "",
                direction=cluster.dominant_direction,
                confidence=adjusted_confidence,
                source_count=len(cluster.signals),
                unique_factor_count=unique_sources,
                cluster_info={
                    "cluster_id": cluster.cluster_id,
                    "original_confidence": cluster.confidence,
                    "adjusted_weight": adjusted_weight,
                    "factor_sources": cluster.factor_sources,
                },
            ))

        return aggregated

    def _calculate_source_exposure(
        self,
        signals: list[Signal],
        source_grouped: dict[str, list[Signal]],
    ) -> float:
        """Calculate exposure to single factor source."""
        if not signals:
            return 0.0

        source_counts: dict[str, int] = {}
        for signal in signals:
            for source, group_signals in source_grouped.items():
                if signal in group_signals:
                    source_counts[source] = source_counts.get(source, 0) + 1

        if not source_counts:
            return 0.0

        max_source_count = max(source_counts.values())
        return max_source_count / len(signals)

    def validate_signals(
        self,
        signals: list[Signal],
        min_agreement: float = 0.6,
    ) -> list[Signal]:
        """Validate signals through cross-validation."""
        if len(signals) < 2:
            return signals

        symbol_signals: dict[str, list[Signal]] = {}
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)

        validated = []

        for symbol, sym_signals in symbol_signals.items():
            if len(sym_signals) < 2:
                validated.extend(sym_signals)
                continue

            directions = [s.direction.upper() for s in sym_signals]
            unique_directions = set(directions)

            if len(unique_directions) == 1:
                validated.extend(sym_signals)
            else:
                direction_counts = {d: directions.count(d) for d in unique_directions}
                max_count = max(direction_counts.values())
                agreement = max_count / len(directions)

                if agreement >= min_agreement:
                    dominant = max(direction_counts, key=direction_counts.get)
                    for s in sym_signals:
                        s.direction = dominant
                    validated.extend(sym_signals)
                else:
                    logger.warning(f"Low agreement for {symbol}: {agreement:.2%}")
                    validated.extend(sym_signals)

        return validated


_global_coordinator: SignalCoordinator | None = None


def get_signal_coordinator() -> SignalCoordinator:
    """Get singleton signal coordinator."""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = SignalCoordinator()
    return _global_coordinator
