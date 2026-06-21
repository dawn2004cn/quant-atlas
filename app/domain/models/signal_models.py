from __future__ import annotations
"""Trading signal domain models."""


import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class SignalType(str, Enum):
    BREAKOUT = "breakout"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    MULTI_FACTOR = "multi_factor"


class SignalStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class SignalSource(str, Enum):
    TECHNICAL = "technical"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    FUNDAMENTAL = "fundamental"
    COMPOSITE = "composite"


class TradingSignal:
    """A generated trading signal."""

    def __init__(
        self,
        *,
        id: str | None = None,
        code: str,
        name: str = "",
        signal_type: SignalType,
        strength: SignalStrength,
        direction: SignalDirection,
        price: float,
        target_price: float | None = None,
        stop_loss: float | None = None,
        confidence: float = 50.0,
        reason: str = "",
        source: SignalSource = SignalSource.TECHNICAL,
        generated_at: datetime | None = None,
        expired_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = id or str(uuid.uuid4())[:12]
        self.code = code
        self.name = name
        self.signal_type = signal_type
        self.strength = strength
        self.direction = direction
        self.price = price
        self.target_price = target_price
        self.stop_loss = stop_loss
        self.confidence = confidence
        self.reason = reason
        self.source = source
        self.generated_at = generated_at or datetime.utcnow()
        self.expired_at = expired_at
        self.metadata = metadata or {}


def _build_breakout(
    code: str,
    name: str,
    price: float,
    volume: float,
    high: float,
    low: float,
    open_price: float,
    prev_close: float,
    avg_volume_20d: float,
) -> TradingSignal:
    av = max(avg_volume_20d, 1.0)
    vol_ratio = volume / av
    breakout_strength = (price - prev_close) / prev_close * 100 if prev_close else 0.0
    near_high = (high - price) / high * 100 if high else 100.0

    if vol_ratio >= 1.5 and (breakout_strength > 0 or near_high < 3):
        strength = SignalStrength.STRONG
    elif vol_ratio >= 1.1 or breakout_strength > -0.5:
        strength = SignalStrength.MODERATE
    else:
        strength = SignalStrength.WEAK

    reason = (
        f"Breakout: vol_ratio={vol_ratio:.2f}, vs_pc={breakout_strength:.2f}%, near_high={near_high:.2f}%"
    )
    tgt = high * 1.02 if high else price * 1.02
    sl = low * 0.98 if low else price * 0.97
    conf = min(95.0, 40.0 + vol_ratio * 15.0 + abs(breakout_strength))

    return TradingSignal(
        code=code,
        name=name,
        signal_type=SignalType.BREAKOUT,
        strength=strength,
        direction=SignalDirection.LONG if price >= prev_close else SignalDirection.SHORT,
        price=price,
        target_price=tgt,
        stop_loss=sl,
        confidence=conf,
        reason=reason,
        source=SignalSource.TECHNICAL,
        expired_at=datetime.utcnow() + timedelta(days=1),
    )


class SignalGenerator:
    """Factory for common signal patterns."""

    @staticmethod
    def generate_breakout_signal(*args: Any, **kwargs: Any) -> TradingSignal:
        """Full OHLC (keyword) or compact positional (code, price, high, volume, avg_volume)."""
        if len(args) == 5 and not kwargs:
            code, price, high, volume, avg_volume_20d = args
            pc = float(price)
            op = pc
            lo = pc * 0.98
            hi = float(high)
            return _build_breakout(
                str(code),
                "",
                float(price),
                float(volume),
                hi,
                lo,
                op,
                pc,
                float(avg_volume_20d),
            )

        req = (
            "code",
            "name",
            "price",
            "volume",
            "high",
            "low",
            "open_price",
            "prev_close",
            "avg_volume_20d",
        )
        for k in req:
            if k not in kwargs:
                raise TypeError(f"generate_breakout_signal missing {k!r}")
        return _build_breakout(
            str(kwargs["code"]),
            str(kwargs["name"]),
            float(kwargs["price"]),
            float(kwargs["volume"]),
            float(kwargs["high"]),
            float(kwargs["low"]),
            float(kwargs["open_price"]),
            float(kwargs["prev_close"]),
            float(kwargs["avg_volume_20d"]),
        )

    @staticmethod
    def generate_volume_signal(
        code: str,
        name: str,
        price: float,
        volume: float,
        avg_volume_20d: float,
    ) -> TradingSignal:
        ratio = volume / avg_volume_20d if avg_volume_20d > 0 else 0.0
        if ratio >= 3:
            strength = SignalStrength.STRONG
        elif ratio >= 2:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        return TradingSignal(
            code=code,
            name=name,
            signal_type=SignalType.VOLUME,
            strength=strength,
            direction=SignalDirection.LONG,
            price=price,
            confidence=min(92.0, 45.0 + ratio * 10.0),
            reason=f"Volume spike: {ratio:.2f}x 20d avg",
            source=SignalSource.VOLUME,
        )

    @staticmethod
    def generate_momentum_signal(
        code: str,
        name: str,
        price: float,
        change_pct: float,
        rsi: float | None = None,
        macd: Any = None,
    ) -> TradingSignal:
        direction = SignalDirection.LONG if change_pct >= 0 else SignalDirection.SHORT
        score = abs(change_pct)
        if rsi is not None:
            score += abs(rsi - 50) / 50.0 * 5
        if isinstance(macd, dict):
            score += abs(float(macd.get("histogram", 0) or 0))
        elif isinstance(macd, int | float):
            score += abs(float(macd)) * 2

        if score >= 8:
            strength = SignalStrength.STRONG
        elif score >= 5:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        return TradingSignal(
            code=code,
            name=name,
            signal_type=SignalType.MOMENTUM,
            strength=strength,
            direction=direction,
            price=price,
            confidence=min(90.0, 35.0 + score * 4.0),
            reason=f"Momentum change_pct={change_pct:.2f}%, rsi={rsi}",
            source=SignalSource.MOMENTUM,
        )

    @staticmethod
    def generate_mean_reversion_signal(
        code: str,
        current_price: float,
        ma_20: float,
        bb_lower: float,
        rsi: float,
    ) -> TradingSignal | None:
        if rsi >= 35 or current_price >= bb_lower:
            return None
        strength = SignalStrength.MODERATE if rsi < 30 else SignalStrength.WEAK
        return TradingSignal(
            code=code,
            name="",
            signal_type=SignalType.MEAN_REVERSION,
            strength=strength,
            direction=SignalDirection.LONG,
            price=current_price,
            target_price=ma_20,
            stop_loss=bb_lower * 0.97,
            confidence=min(85.0, 60.0 + (30 - rsi)),
            reason=f"Oversold reversion: rsi={rsi:.1f}, price vs bb_lower",
            source=SignalSource.TECHNICAL,
        )

    @staticmethod
    def generate_multi_factor_signal(
        code: str,
        name: str,
        price: float,
        indicators: dict[str, Any],
    ) -> TradingSignal:
        rsi = float(indicators.get("rsi") or indicators.get("rsi_14") or 50)
        vol_ratio = float(indicators.get("volume_ratio", 1.0))
        score = (vol_ratio - 1.0) * 20 + abs(rsi - 50) / 50.0 * 30
        strength = (
            SignalStrength.STRONG if score > 25 else SignalStrength.MODERATE if score > 12 else SignalStrength.WEAK
        )
        direction = SignalDirection.LONG if rsi < 70 else SignalDirection.SHORT
        return TradingSignal(
            code=code,
            name=name,
            signal_type=SignalType.MULTI_FACTOR,
            strength=strength,
            direction=direction,
            price=price,
            confidence=min(88.0, 40.0 + score),
            reason=f"Multi-factor score={score:.1f}",
            source=SignalSource.COMPOSITE,
            metadata=dict(indicators),
        )

    @staticmethod
    def evaluate_signal(signal: TradingSignal) -> dict[str, Any]:
        """Lightweight signal quality / action hint."""
        strength_rank = {SignalStrength.WEAK: 0, SignalStrength.MODERATE: 1, SignalStrength.STRONG: 2}
        rank = strength_rank.get(signal.strength, 0)
        if rank >= 2 and signal.confidence >= 60:
            action = "enter"
        elif rank == 0 or signal.confidence < 40:
            action = "ignore"
        else:
            action = "watch"
        return {
            "action": action,
            "confidence": signal.confidence,
            "strength": signal.strength.value,
            "direction": signal.direction.value,
        }
