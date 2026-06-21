"""Psychology Layer — Phase 13. AI Trading Coach with FOMO/revenge detection."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.modules.execution.services.trade_outcome_review_service import TradeOutcomeReviewService
from app.domain.risk.risk_companion_models import SentimentProfile

logger = get_logger(__name__)


@dataclass
class BehaviorDiagnosis:
    user_id: int
    diagnosis_type: str  # "fomo", "revenge", "euphoric", "panic", "normal"
    score: float  # 0..1 severity
    description: str = ""
    suggestion: str = ""
    recent_trades: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PsychologyCoachService:
    """Trading psychology coach — analyses behaviour, gives corrective advice."""

    def __init__(self, review_service: TradeOutcomeReviewService | None = None):
        self._review = review_service or TradeOutcomeReviewService()

    def diagnose(self, user_id: int) -> BehaviorDiagnosis:
        """Analyse user trading behaviour and diagnose issues."""
        try:
            reviews = self._review.get_user_reviews(user_id, limit=20)
        except Exception:
            return BehaviorDiagnosis(user_id=user_id, diagnosis_type="normal", score=0.0)

        if not reviews:
            return BehaviorDiagnosis(user_id=user_id, diagnosis_type="normal", score=0.0)

        total = len(reviews)
        consecutive_losses = 0
        max_consecutive = 0
        fomo_trades = 0
        total_loss = 0.0

        for r in reviews:
            pnl = getattr(r, 'pnl', 0) or getattr(r, 'profit_loss', 0) or 0
            if pnl < 0:
                consecutive_losses += 1
                total_loss += abs(pnl)
                if consecutive_losses > max_consecutive:
                    max_consecutive = consecutive_losses
            else:
                consecutive_losses = 0
            # FOMO heuristic: buy after gap up
            if getattr(r, 'trade_reason', '') == 'gap_up':
                fomo_trades += 1

        # Diagnose
        if max_consecutive >= 5:
            return BehaviorDiagnosis(
                user_id=user_id, diagnosis_type="revenge", score=min(1.0, max_consecutive / 10),
                description=f"检测到连续 {max_consecutive} 笔亏损，可能进入报复性交易模式",
                suggestion="建议暂停交易 1 小时，设置硬止损线，复盘亏损原因",
                recent_trades=total,
            )
        if fomo_trades >= 3 and total_loss > 0:
            return BehaviorDiagnosis(
                user_id=user_id, diagnosis_type="fomo", score=min(1.0, fomo_trades / 5),
                description=f"检测到 {fomo_trades} 笔FOMO追涨交易",
                suggestion="建议使用限价单而非市价单，设置买入冷静期",
                recent_trades=total,
            )
        if total_loss > 0 and max_consecutive >= 3:
            return BehaviorDiagnosis(
                user_id=user_id, diagnosis_type="panic", score=min(1.0, total_loss / 10000),
                description="检测到恐慌性交易行为",
                suggestion="建议降低仓位，开启RiskCompanion干预",
                recent_trades=total,
            )

        return BehaviorDiagnosis(user_id=user_id, diagnosis_type="normal", score=0.0,
                                description="交易行为正常", suggestion="继续保持纪律性交易")
