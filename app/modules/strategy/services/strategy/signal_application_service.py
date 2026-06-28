from __future__ import annotations
"""Signal application service with domain model integration."""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.models.signal_models import (
    SignalGenerator,
    TradingSignal,
    SignalType,
    SignalStrength,
    SignalSource,
    SignalDirection,
)
from app.application.dto.complete_dto import (
    SignalDTO,
    SignalFilterDTO,
)
from app.application.events.event_bus import EventBus, EventType, publish_event

logger = get_logger(__name__)


class SignalApplicationService:
    """Application service for signal generation and management."""

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus or EventBus()
        self._signal_cache: dict[str, list[TradingSignal]] = {}
        logger.info("SignalApplicationService initialized")

    async def generate_breakout_signal(
        self,
        code: str,
        name: str,
        price: float,
        volume: float,
        high: float,
        low: float,
        open_price: float,
        prev_close: float,
        avg_volume_20d: float,
        source: SignalSource = SignalSource.TECHNICAL,
    ) -> SignalDTO:
        """Generate a breakout signal using domain model."""
        signal = SignalGenerator.generate_breakout_signal(
            code=code,
            name=name,
            price=price,
            volume=volume,
            high=high,
            low=low,
            open_price=open_price,
            prev_close=prev_close,
            avg_volume_20d=avg_volume_20d,
        )

        dto = self._signal_to_dto(signal)

        await publish_event(
            EventType.SIGNAL_GENERATED,
            {"code": code, "signal_type": signal.signal_type.value},
            source="SignalApplicationService"
        )

        return dto

    async def generate_volume_signal(
        self,
        code: str,
        name: str,
        price: float,
        volume: float,
        avg_volume_20d: float,
        source: SignalSource = SignalSource.VOLUME,
    ) -> SignalDTO:
        """Generate a volume-based signal."""
        signal = SignalGenerator.generate_volume_signal(
            code=code,
            name=name,
            price=price,
            volume=volume,
            avg_volume_20d=avg_volume_20d,
        )
        return self._signal_to_dto(signal)

    async def generate_momentum_signal(
        self,
        code: str,
        name: str,
        price: float,
        change_pct: float,
        rsi: float | None = None,
        macd: float | None = None,
        source: SignalSource = SignalSource.MOMENTUM,
    ) -> SignalDTO:
        """Generate momentum-based signal."""
        signal = SignalGenerator.generate_momentum_signal(
            code=code,
            name=name,
            price=price,
            change_pct=change_pct,
            rsi=rsi,
            macd=macd,
        )
        return self._signal_to_dto(signal)

    async def generate_multi_factor_signal(
        self,
        code: str,
        name: str,
        price: float,
        indicators: dict[str, Any],
    ) -> SignalDTO:
        """Generate signal from multiple factors."""
        signal = SignalGenerator.generate_multi_factor_signal(
            code=code,
            name=name,
            price=price,
            indicators=indicators,
        )
        return self._signal_to_dto(signal)

    async def process_stock_signals(
        self,
        code: str,
        name: str,
        market_data: dict[str, Any],
    ) -> list[SignalDTO]:
        """Process all signals for a stock."""
        signals = []

        price = market_data.get("price", 0)
        volume = market_data.get("volume", 0)
        high = market_data.get("high", price)
        low = market_data.get("low", price)
        open_price = market_data.get("open", price)
        prev_close = market_data.get("prev_close", price)
        avg_volume = market_data.get("avg_volume_20d", volume)

        breakout = await self.generate_breakout_signal(
            code, name, price, volume, high, low, open_price, prev_close, avg_volume
        )
        if breakout.strength in ["strong", "moderate"]:
            signals.append(breakout)

        volume_signal = await self.generate_volume_signal(
            code, name, price, volume, avg_volume
        )
        if volume_signal.strength in ["strong", "moderate"]:
            signals.append(volume_signal)

        change_pct = market_data.get("change_pct", 0)
        rsi = market_data.get("rsi")
        macd = market_data.get("macd")

        if change_pct != 0 or rsi is not None:
            momentum = await self.generate_momentum_signal(
                code, name, price, change_pct, rsi, macd
            )
            if momentum.strength in ["strong", "moderate"]:
                signals.append(momentum)

        if signals:
            self._signal_cache[code] = [self._dto_to_signal(s) for s in signals]
            await publish_event(
                EventType.SIGNALS_BATCH_PROCESSED,
                {"code": code, "count": len(signals)},
                source="SignalApplicationService"
            )

        return signals

    def get_signals_for_stock(self, code: str) -> list[SignalDTO]:
        """Get cached signals for a stock."""
        cached = self._signal_cache.get(code, [])
        return [self._signal_to_dto(s) for s in cached]

    def filter_signals(
        self,
        signals: list[SignalDTO],
        filter_dto: SignalFilterDTO,
    ) -> list[SignalDTO]:
        """Filter signals based on criteria."""
        result = signals

        if filter_dto.signal_types:
            result = [s for s in result if s.signal_type in filter_dto.signal_types]

        if filter_dto.min_strength:
            strength_order = {"weak": 0, "moderate": 1, "strong": 2}
            min_level = strength_order.get(filter_dto.min_strength, 0)
            result = [
                s for s in result
                if strength_order.get(s.strength, 0) >= min_level
            ]

        if filter_dto.code_list:
            result = [s for s in result if s.code in filter_dto.code_list]

        return result

    def _signal_to_dto(self, signal: TradingSignal) -> SignalDTO:
        """Convert domain signal to DTO."""
        return SignalDTO(
            id=signal.id,
            code=signal.code,
            name=signal.name,
            signal_type=signal.signal_type.value,
            strength=signal.strength.value,
            direction=signal.direction.value,
            price=signal.price,
            target_price=signal.target_price,
            stop_loss=signal.stop_loss,
            confidence=signal.confidence,
            reason=signal.reason,
            source=signal.source.value,
            generated_at=signal.generated_at.isoformat(),
            expired_at=signal.expired_at.isoformat() if signal.expired_at else None,
            metadata=signal.metadata,
        )

    def _dto_to_signal(self, dto: SignalDTO) -> TradingSignal:
        """Convert DTO back to domain signal."""
        return TradingSignal(
            id=dto.id,
            code=dto.code,
            name=dto.name,
            signal_type=SignalType(dto.signal_type),
            strength=SignalStrength(dto.strength),
            direction=SignalDirection(dto.direction),
            price=dto.price,
            target_price=dto.target_price,
            stop_loss=dto.stop_loss,
            confidence=dto.confidence,
            reason=dto.reason,
            source=SignalSource(dto.source),
            generated_at=datetime.fromisoformat(dto.generated_at),
            expired_at=datetime.fromisoformat(dto.expired_at) if dto.expired_at else None,
            metadata=dto.metadata or {},
        )

    def clear_cache(self, code: str | None = None):
        """Clear signal cache."""
        if code:
            self._signal_cache.pop(code, None)
        else:
            self._signal_cache.clear()


__all__ = ["SignalApplicationService"]
