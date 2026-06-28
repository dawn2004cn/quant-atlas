"""Risk Companion domain models — emotion detection, empathy, XP system.

These models sit alongside the existing risk_models.py (RiskCalculator, RiskMetrics)
and provide the emotional-intelligence layer on top of the cold numerical risk checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Emotion patterns
# ---------------------------------------------------------------------------


class EmotionPattern(str, Enum):
    """Detected emotional trading patterns."""

    NONE = "none"
    OVERTRADING = "overtrading"
    FOMO = "fomo"
    REVENGE_TRADING = "revenge"
    CONFIRMATION_BIAS = "confirmation"


class EmpathyTone(str, Enum):
    """Tone of the companion's response."""

    CALM_REASSURING = "calm"
    WARM_CAUTIONARY = "warm_caution"
    WITTY_DISTRACTION = "witty"
    FIRM_BOUNDARY = "firm"


class XpEventType(str, Enum):
    """Events that earn XP rewards."""

    PRUDENT_STOP_LOSS = "prudent_stop_loss"
    NO_OVERTRADING_DAY = "no_overtrade"
    FOLLOWED_RISK_PLAN = "followed_plan"
    USED_EVIDENCE_CARD = "used_evidence"
    ACCEPTED_MISSING_OUT = "accepted_missing_out"
    AWAITED_CONFIRMATION = "awaited_confirmation"


# ---------------------------------------------------------------------------
# Message model
# ---------------------------------------------------------------------------


@dataclass
class RiskCompanionMessage:
    """A warm, empathetic message instead of a cold warning."""

    tone: EmpathyTone
    headline: str
    body: str
    actionable_suggestion: str
    risk_level: str  # LOW / MEDIUM / HIGH / EXTREME

    def to_dict(self) -> dict[str, Any]:
        return {
            "tone": self.tone.value,
            "headline": self.headline,
            "body": self.body,
            "actionable_suggestion": self.actionable_suggestion,
            "risk_level": self.risk_level,
        }


# ---------------------------------------------------------------------------
# Emotion signal
# ---------------------------------------------------------------------------


@dataclass
class EmotionSignal:
    """A detected emotional trading pattern."""

    pattern: EmotionPattern
    confidence: float  # 0.0 – 1.0
    evidence_summary: str
    suggested_tone: EmpathyTone

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern.value,
            "confidence": round(self.confidence, 3),
            "evidence_summary": self.evidence_summary,
            "suggested_tone": self.suggested_tone.value,
        }


# ---------------------------------------------------------------------------
# XP model
# ---------------------------------------------------------------------------


@dataclass
class XpEntry:
    """One XP reward event."""

    event_type: XpEventType
    points: int
    context: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "points": self.points,
            "context": self.context,
        }


# ---------------------------------------------------------------------------
# Trading DNA profile
# ---------------------------------------------------------------------------


@dataclass
class SentimentProfile:
    user_id: int
    recent_loss_count: int = 0
    win_rate_24h: float = 0.0
    trade_frequency: int = 0
    trade_size_avg: float = 0.0
    normal_trade_size: float = 1.0
    position_volatility: float = 0.0
    tilt_duration_sec: int = 0
    risk_level: str = "LOW"


class RiskCompanionService:
    def assess_user_risk_profile(self, user_id: int) -> SentimentProfile:
        return SentimentProfile(user_id=user_id)

    def format_sentiment_warning(self, profile: SentimentProfile, triggers: list[str]) -> str:
        return f"Risk companion noticed {', '.join(triggers) or 'risk tilt'} for user {profile.user_id}."

    def should_intervene(self, user_id: int, narrative: str) -> bool:
        return False


@dataclass
class TradingDNAProfile:
    """User's trading DNA spiral data for visualization."""

    user_id: str
    total_xp: int = 0
    prudent_actions: int = 0
    reckless_actions: int = 0
    streak_days: int = 0
    xp_history: list[XpEntry] = field(default_factory=list)
    risk_companion_messages_sent: int = 0

    @property
    def is_balanced(self) -> bool:
        return self.prudent_actions >= self.reckless_actions

    @property
    def balance_ratio(self) -> float:
        total = self.prudent_actions + self.reckless_actions
        if total == 0:
            return 0.5
        return self.prudent_actions / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_xp": self.total_xp,
            "prudent_actions": self.prudent_actions,
            "reckless_actions": self.reckless_actions,
            "streak_days": self.streak_days,
            "is_balanced": self.is_balanced,
            "balance_ratio": round(self.balance_ratio, 3),
            "xp_history": [e.to_dict() for e in self.xp_history[-50:]],
            "risk_companion_messages_sent": self.risk_companion_messages_sent,
        }
