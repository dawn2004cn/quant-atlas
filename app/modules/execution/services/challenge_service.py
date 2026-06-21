from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Investment Manager Challenge & Leaderboard System."""


import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


from app.core.logger import get_logger

logger = get_logger(__name__)


class ChallengeStatus(Enum):
    """Challenge status."""
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChallengePeriod(Enum):
    """Challenge period type."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class ChallengeConfig:
    """Configuration for a challenge."""
    name: str
    description: str
    period: ChallengePeriod
    start_date: datetime
    end_date: datetime
    initial_capital: float = 1000000.0
    min_positions: int = 1
    max_positions: int = 20
    allow_short: bool = False
    allow_options: bool = False


@dataclass
class Participant:
    """Challenge participant."""
    user_id: str
    nickname: str
    strategy_name: str
    current_value: float = 0.0
    total_return: float = 0.0
    rank: int = 0
    trades_count: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    
    # Public profile (for sharing)
    is_public: bool = False
    avatar: str = ""


@dataclass
class Leaderboard:
    """Leaderboard for a challenge."""
    challenge_id: str
    participants: List[Participant] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_top(self, n: int = 10) -> List[Participant]:
        """Get top N participants."""
        return sorted(self.participants, key=lambda x: x.total_return, reverse=True)[:n]
    
    def get_user_rank(self, user_id: str) -> Optional[int]:
        """Get user's rank."""
        for p in self.participants:
            if p.user_id == user_id:
                return p.rank
        return None


@dataclass
class Challenge:
    """Investment challenge."""
    challenge_id: str
    config: ChallengeConfig
    status: ChallengeStatus = ChallengeStatus.UPCOMING
    leaderboard: Optional[Leaderboard] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    winner_id: Optional[str] = None


class ChallengeManager:
    """Manager for investment challenges."""

    def __init__(self):
        self._challenges: Dict[str, Challenge] = {}
        self._leaderboard_cache: Dict[str, Leaderboard] = {}

    def create_challenge(
        self,
        name: str,
        description: str,
        period: ChallengePeriod,
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> Challenge:
        """Create a new challenge."""
        config = ChallengeConfig(
            name=name,
            description=description,
            period=period,
            start_date=start_date,
            end_date=end_date,
            *kwargs
        )

        challenge = Challenge(
            challenge_id=f"challenge_{len(self._challenges) + 1}",
            config=config,
            status=ChallengeStatus.UPCOMING
        )

        self._challenges[challenge.challenge_id] = challenge
        logger.info(f"Created challenge: {name}")
        
        return challenge

    def start_challenge(self, challenge_id: str) -> bool:
        """Start a challenge."""
        if challenge_id not in self._challenges:
            return False

        challenge = self._challenges[challenge_id]
        challenge.status = ChallengeStatus.ACTIVE
        challenge.leaderboard = Leaderboard(challenge_id=challenge_id)
        
        return True

    def join_challenge(
        self,
        challenge_id: str,
        user_id: str,
        nickname: str,
        strategy_name: str
    ) -> bool:
        """Join a challenge."""
        if challenge_id not in self._challenges:
            return False

        challenge = self._challenges[challenge_id]
        
        participant = Participant(
            user_id=user_id,
            nickname=nickname,
            strategy_name=strategy_name,
            current_value=challenge.config.initial_capital,
            total_return=0.0
        )

        if not challenge.leaderboard:
            challenge.leaderboard = Leaderboard(challenge_id=challenge_id)

        challenge.leaderboard.participants.append(participant)
        
        logger.info(f"User {user_id} joined challenge {challenge_id}")
        return True

    def update_performance(
        self,
        challenge_id: str,
        user_id: str,
        current_value: float,
        trades_count: int = 0,
        win_rate: float = 0.0,
        max_drawdown: float = 0.0
    ) -> bool:
        """Update participant's performance."""
        if challenge_id not in self._challenges:
            return False

        challenge = self._challenges[challenge_id]
        if not challenge.leaderboard:
            return False

        initial = challenge.config.initial_capital
        total_return = ((current_value - initial) / initial) * 100

        for p in challenge.leaderboard.participants:
            if p.user_id == user_id:
                p.current_value = current_value
                p.total_return = total_return
                p.trades_count = trades_count
                p.win_rate = win_rate
                p.max_drawdown = max_drawdown

        self._recalculate_ranks(challenge_id)
        return True

    def _recalculate_ranks(self, challenge_id: str) -> None:
        """Recalculate participant ranks."""
        challenge = self._challenges.get(challenge_id)
        if not challenge or not challenge.leaderboard:
            return

        sorted_participants = sorted(
            challenge.leaderboard.participants,
            key=lambda x: x.total_return,
            reverse=True
        )

        for i, p in enumerate(sorted_participants):
            p.rank = i + 1

        challenge.leaderboard.updated_at = datetime.now()

    def get_leaderboard(self, challenge_id: str) -> Optional[Leaderboard]:
        """Get leaderboard for a challenge."""
        return self._challenges.get(challenge_id, {}).leaderboard

    def get_active_challenges(self) -> List[Challenge]:
        """Get all active challenges."""
        return [
            c for c in self._challenges.values()
            if c.status == ChallengeStatus.ACTIVE
        ]

    def get_user_challenges(self, user_id: str) -> List[Dict]:
        """Get challenges a user is participating in."""
        result = []
        
        for c in self._challenges.values():
            if c.leaderboard:
                for p in c.leaderboard.participants:
                    if p.user_id == user_id:
                        result.append({
                            "challenge_id": c.challenge_id,
                            "name": c.config.name,
                            "status": c.status.value,
                            "rank": p.rank,
                            "total_return": p.total_return,
                            "current_value": p.current_value
                        })

        return result


# Share strategy without revealing real data
def create_shareable_strategy(profile: Participant, hide_details: bool = True) -> Dict:
    """Create a shareable strategy profile (without real data)."""
    if hide_details:
        return {
            "nickname": profile.nickname,
            "strategy_name": profile.strategy_name,
            "rank": profile.rank,
            "total_return": f"{profile.total_return:.1f}%",
            "win_rate": f"{profile.win_rate:.0f}%" if profile.win_rate > 0 else "N/A",
            "style": "保守" if profile.max_drawdown < 10 else ("激进" if profile.max_drawdown > 20 else "均衡"),
            "join_date": "最近"
        }
    
    return {
        "nickname": profile.nickname,
        "strategy_name": profile.strategy_name,
        "rank": profile.rank,
        "total_return": profile.total_return,
        "current_value": profile.current_value,
        "trades_count": profile.trades_count,
        "win_rate": profile.win_rate,
        "max_drawdown": profile.max_drawdown
    }


__all__ = [
    "ChallengeStatus",
    "ChallengePeriod",
    "ChallengeConfig",
    "Participant",
    "Leaderboard",
    "Challenge",
    "ChallengeManager",
    "create_shareable_strategy"
]