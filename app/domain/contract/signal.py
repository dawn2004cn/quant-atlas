from __future__ import annotations
"""Signal Contract - Unified Signal representation."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SignalType(Enum):
    """Type of trading signal."""
    LONG = "long"
    SHORT = "short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    NEUTRAL = "neutral"


class SignalStrength(Enum):
    """Strength of the signal."""
    WEAK = 0.25
    MODERATE = 0.5
    STRONG = 0.75
    VERY_STRONG = 1.0


@dataclass
class Signal:
    """Unified Signal representation for trading decisions.

    This is the canonical form that all agents must produce when
    making trading recommendations.
    """
    id: str
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    timestamp: datetime

    source_agent: str
    confidence: float = 0.5

    alpha_id: str | None = None
    model_id: str | None = None

    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    target_price: float | None = None
    stop_loss: float | None = None
    position_size: float | None = None

    def is_actionable(self) -> bool:
        """Check if signal is actionable."""
        return (
            self.confidence >= 0.5
            and self.signal_type in [SignalType.LONG, SignalType.SHORT]
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "strength": self.strength.value,
            "timestamp": self.timestamp.isoformat(),
            "source_agent": self.source_agent,
            "confidence": self.confidence,
            "alpha_id": self.alpha_id,
            "model_id": self.model_id,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "position_size": self.position_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            symbol=data["symbol"],
            signal_type=SignalType(data["signal_type"]),
            strength=SignalStrength(data["strength"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source_agent=data["source_agent"],
            confidence=data.get("confidence", 0.5),
            alpha_id=data.get("alpha_id"),
            model_id=data.get("model_id"),
            reasoning=data.get("reasoning", ""),
            metadata=data.get("metadata", {}),
            target_price=data.get("target_price"),
            stop_loss=data.get("stop_loss"),
            position_size=data.get("position_size"),
        )