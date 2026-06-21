"""Evolution Arbiter domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Regime(str, Enum):
    BULL_STRONG = "bull_strong"
    BULL_WEAK = "bull_weak"
    BEAR_STRONG = "bear_strong"
    BEAR_WEAK = "bear_weak"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class StrategyBias(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"
    HEDGE = "hedge"


@dataclass
class RegimeSnapshot:
    regime: Regime
    confidence: float
    source: str = ""
    captured_at: datetime = field(default_factory=datetime.now)


@dataclass
class ChampionStrategy:
    strategy_id: str
    name: str
    bias: StrategyBias
    performance_score: float = 0.0
    deployed_at: datetime | None = None


@dataclass
class ChallengerResult:
    strategy_id: str
    name: str
    bias: StrategyBias
    shadow_pnl: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0


@dataclass
class EvolutionState:
    current_regime: Regime = Regime.UNKNOWN
    champion: ChampionStrategy | None = None
    challengers: list[ChallengerResult] = field(default_factory=list)
    last_evolution_at: datetime | None = None
    evolution_count: int = 0
