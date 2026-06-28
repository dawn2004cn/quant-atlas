from __future__ import annotations

"""Signal Generation Domain Service.

Pure domain logic for signal creation and quality scoring.
"""


from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class SignalStrength(str, Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class SignalSource(str, Enum):
    """Signal sources."""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MOMENTUM = "momentum"
    VALUE = "value"
    NEWS = "news"
    COMPOSITE = "composite"


@dataclass(frozen=True)
class SignalConfig:
    """Configuration for signal generation."""
    source: SignalSource
    threshold_strong: float = 0.7
    threshold_moderate: float = 0.4
    expiry_days: int = 7


@dataclass(frozen=True)
class GeneratedSignal:
    """A generated signal with metadata."""
    stock_code: str
    signal_type: str  # buy, sell, hold
    confidence: float
    source: SignalSource
    reason: str
    generated_at: datetime
    expires_at: datetime | None = None

    @property
    def strength(self) -> SignalStrength:
        if self.confidence >= 0.8:
            return SignalStrength.VERY_STRONG
        elif self.confidence >= 0.7:
            return SignalStrength.STRONG
        elif self.confidence >= 0.4:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_bullish(self) -> bool:
        return self.signal_type in ("buy", "strong_buy")

    @property
    def is_bearish(self) -> bool:
        return self.signal_type in ("sell", "strong_sell")


class SignalGenerationService:
    """Domain service for signal generation."""

    def __init__(self, config: SignalConfig | None = None):
        self._config = config or SignalConfig(source=SignalSource.TECHNICAL)

    def generate_from_technical(
        self,
        stock_code: str,
        indicators: dict
    ) -> GeneratedSignal:
        """Generate signal from technical indicators."""
        signal_type = "hold"
        confidence = 0.5
        reason = "Neutral"

        ma5 = indicators.get("ma5", 0)
        ma20 = indicators.get("ma20", 0)
        indicators.get("ma60", 0)
        rsi = indicators.get("rsi", 50)
        price = indicators.get("close", 0)

        if ma5 and ma20 and price:
            if ma5 > ma20 and price > ma5:
                signal_type = "buy"
                confidence = 0.7
                reason = "Golden cross - MA5 > MA20"
            elif ma5 < ma20 and price < ma5:
                signal_type = "sell"
                confidence = 0.7
                reason = "Death cross - MA5 < MA20"

        if rsi:
            if rsi > 80:
                signal_type = "sell"
                confidence = max(confidence, 0.8)
                reason = f"RSI overbought {rsi:.0f}"
            elif rsi < 20:
                signal_type = "buy"
                confidence = max(confidence, 0.8)
                reason = f"RSI oversold {rsi:.0f}"

        expires_at = datetime.now() + timedelta(days=self._config.expiry_days)

        return GeneratedSignal(
            stock_code=stock_code,
            signal_type=signal_type,
            confidence=confidence,
            source=SignalSource.TECHNICAL,
            reason=reason,
            generated_at=datetime.now(),
            expires_at=expires_at,
        )

    def generate_from_momentum(
        self,
        stock_code: str,
        returns: dict
    ) -> GeneratedSignal:
        """Generate signal from momentum indicators."""
        signal_type = "hold"
        confidence = 0.5
        reason = "Neutral"

        d1_return = returns.get("1d", 0)
        w1_return = returns.get("1w", 0)
        m1_return = returns.get("1m", 0)

        if d1_return > 5 and w1_return > 15:
            signal_type = "sell"
            confidence = 0.7
            reason = "Short-term momentum overbought"
        elif d1_return < -5 and w1_return < -15:
            signal_type = "buy"
            confidence = 0.7
            reason = "Short-term momentum oversold"
        elif m1_return > 30:
            signal_type = "sell"
            confidence = 0.6
            reason = "Monthly momentum strong"
        elif m1_return < -30:
            signal_type = "buy"
            confidence = 0.6
            reason = "Monthly momentum weak"

        expires_at = datetime.now() + timedelta(days=3)

        return GeneratedSignal(
            stock_code=stock_code,
            signal_type=signal_type,
            confidence=confidence,
            source=SignalSource.MOMENTUM,
            reason=reason,
            generated_at=datetime.now(),
            expires_at=expires_at,
        )

    def aggregate_signals(
        self,
        signals: list[GeneratedSignal]
    ) -> GeneratedSignal:
        """Aggregate multiple signals into one."""
        if not signals:
            return GeneratedSignal(
                stock_code="",
                signal_type="hold",
                confidence=0.0,
                source=SignalSource.COMPOSITE,
                reason="No signals",
                generated_at=datetime.now(),
            )

        if len(signals) == 1:
            return signals[0]

        stock_code = signals[0].stock_code

        buy_count = sum(1 for s in signals if s.is_bullish)
        sell_count = sum(1 for s in signals if s.is_bearish)

        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        if buy_count > sell_count:
            signal_type = "buy"
            reason = f"Aggregated buy signals ({buy_count}/{len(signals)})"
        elif sell_count > buy_count:
            signal_type = "sell"
            reason = f"Aggregated sell signals ({sell_count}/{len(signals)})"
        else:
            signal_type = "hold"
            reason = "Signals balanced"

        return GeneratedSignal(
            stock_code=stock_code,
            signal_type=signal_type,
            confidence=avg_confidence,
            source=SignalSource.COMPOSITE,
            reason=reason,
            generated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=1),
        )

    def score_signal_quality(
        self,
        signal: GeneratedSignal,
        historical_accuracy: dict | None = None
    ) -> float:
        """Score signal quality."""
        quality = signal.confidence

        if signal.strength == SignalStrength.VERY_STRONG:
            quality *= 1.2
        elif signal.strength == SignalStrength.STRONG:
            quality *= 1.0

        if signal.source == SignalSource.TECHNICAL:
            quality *= 1.1
        elif signal.source == SignalSource.COMPOSITE:
            quality *= 1.2

        return min(quality, 1.0)


class SignalAggregator:
    """Aggregate signals from multiple sources."""

    def __init__(self):
        self._service = SignalGenerationService()

    def aggregate_all(
        self,
        stock_code: str,
        technical_indicators: dict,
        momentum_returns: dict
    ) -> GeneratedSignal:
        """Aggregate all signal types."""
        signals = []

        if technical_indicators:
            tech_signal = self._service.generate_from_technical(
                stock_code, technical_indicators
            )
            signals.append(tech_signal)

        if momentum_returns:
            moment_signal = self._service.generate_from_momentum(
                stock_code, momentum_returns
            )
            signals.append(moment_signal)

        return self._service.aggregate_signals(signals)


__all__ = [
    "SignalStrength",
    "SignalSource",
    "SignalConfig",
    "GeneratedSignal",
    "SignalGenerationService",
    "SignalAggregator",
]
