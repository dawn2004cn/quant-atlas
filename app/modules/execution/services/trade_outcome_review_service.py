
"""Trade outcome review service.

Records executed trades and generates structured post-trade retrospectives
3-5 days after execution, using UnifiedAttributionService for win/loss attribution.
(ref: plan 2.4 - Cognitive Review Loop)
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.core.logger import get_logger
from app.domain.dto.analytics_dto import AttributionReportDTO

logger = get_logger(__name__)


@dataclass(frozen=True)
class TradeRecord:
    """A single executed trade captured for later review."""
    trade_id: str
    user_id: int
    symbol: str
    direction: str
    entry_price: float
    quantity: int
    executed_at: str
    market: str = "CN"
    strategy_id: str = "manual"
    exit_price: float | None = None
    exit_at: str | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    review_status: str = "pending"  # pending | reviewed | attributed


@dataclass(frozen=True)
class TradeReviewCard:
    """A structured post-trade review card shown to the user."""
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float | None
    pnl: float | None
    pnl_pct: float | None
    holding_days: int
    attribution: AttributionReportDTO | None = None
    summary: str = ""
    key_lesson: str = ""
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


class TradeOutcomeReviewService:
    """Records trades and auto-generates review cards 3-5 days post-execution."""

    def __init__(
        self,
        *,
        store_path: Path | None = None,
        attribution_service: Any | None = None,
        review_delay_days: int = 3,
    ) -> None:
        self._path = Path(store_path or BASE_DIR / "instance" / "trade_reviews.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if attribution_service is None:
            from app.modules.strategy.services.analytics.unified_attribution_service import UnifiedAttributionService

            attribution_service = UnifiedAttributionService()
        self._attribution = attribution_service
        self._review_delay_days = review_delay_days
        self._trades: dict[str, TradeRecord] = {}
        self._reviews: dict[str, TradeReviewCard] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for t in raw.get("trades", []):
                self._trades[t["trade_id"]] = TradeRecord(**t)
            for r in raw.get("reviews", []):
                self._reviews[r["trade_id"]] = TradeReviewCard(**r)
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            logger.warning("TradeOutcomeReviewService load: %s", exc)

    def _persist(self) -> None:
        try:
            data = {
                "trades": [
                    {"trade_id": t.trade_id, "user_id": t.user_id, "symbol": t.symbol,
                     "direction": t.direction, "entry_price": t.entry_price,
                     "quantity": t.quantity, "executed_at": t.executed_at,
                     "market": t.market, "strategy_id": t.strategy_id,
                     "exit_price": t.exit_price, "exit_at": t.exit_at,
                     "pnl": t.pnl, "pnl_pct": t.pnl_pct, "review_status": t.review_status}
                    for t in self._trades.values()
                ],
                "reviews": [
                    {"trade_id": r.trade_id, "symbol": r.symbol,
                     "direction": r.direction, "entry_price": r.entry_price,
                     "exit_price": r.exit_price, "pnl": r.pnl, "pnl_pct": r.pnl_pct,
                     "holding_days": r.holding_days, "summary": r.summary,
                     "key_lesson": r.key_lesson, "generated_at": r.generated_at}
                    for r in self._reviews.values()
                ],
            }
            self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("TradeOutcomeReviewService persist: %s", exc)

    def record_trade(
        self,
        *,
        trade_id: str,
        user_id: int,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: int,
        market: str = "CN",
        strategy_id: str = "manual",
    ) -> TradeRecord:
        """Record a newly executed trade for future review."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._lock:
            if trade_id in self._trades:
                return self._trades[trade_id]
            rec = TradeRecord(
                trade_id=trade_id,
                user_id=user_id,
                symbol=symbol.strip().upper(),
                direction=direction,
                entry_price=entry_price,
                quantity=quantity,
                executed_at=now,
                market=market,
                strategy_id=strategy_id,
            )
            self._trades[trade_id] = rec
            self._persist()
        return rec

    def close_trade(
        self,
        *,
        trade_id: str,
        exit_price: float,
    ) -> TradeRecord | None:
        """Record exit price and compute P&amp;L, then auto-generate review."""
        with self._lock:
            rec = self._trades.get(trade_id)
            if rec is None or rec.exit_price is not None:
                return rec
            pnl = round((exit_price - rec.entry_price) * rec.quantity, 2)
            pnl_pct = round((exit_price - rec.entry_price) / rec.entry_price * 100, 2)
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            updated = TradeRecord(
                trade_id=rec.trade_id,
                user_id=rec.user_id,
                symbol=rec.symbol,
                direction=rec.direction,
                entry_price=rec.entry_price,
                quantity=rec.quantity,
                executed_at=rec.executed_at,
                market=rec.market,
                strategy_id=rec.strategy_id,
                exit_price=exit_price,
                exit_at=now,
                pnl=pnl,
                pnl_pct=pnl_pct,
                review_status="reviewed",
            )
            self._trades[trade_id] = updated
            review = self._generate_review(updated)
            self._reviews[trade_id] = review
            self._persist()
        return updated

    def get_review(self, trade_id: str) -> TradeReviewCard | None:
        with self._lock:
            return self._reviews.get(trade_id)

    def list_pending_reviews(self, *, limit: int = 20) -> list[TradeReviewCard]:
        with self._lock:
            items = [r for r in self._reviews.values() if r.summary]
        items.sort(key=lambda r: r.generated_at, reverse=True)
        return items[:limit]

    def _generate_review(self, trade: TradeRecord) -> TradeReviewCard:
        """Auto-generate a review card with attribution analysis."""
        try:
            holding_days = 0
            if trade.executed_at and trade.exit_at:
                try:
                    entry_dt = datetime.fromisoformat(trade.executed_at.replace("Z", "+00:00"))
                    exit_dt = datetime.fromisoformat(trade.exit_at.replace("Z", "+00:00"))
                    holding_days = max(1, (exit_dt - entry_dt).days)
                except (ValueError, TypeError):
                    holding_days = self._review_delay_days

            pnl = trade.pnl or 0.0
            pnl_pct = trade.pnl_pct or 0.0

            if pnl > 0:
                key_lesson = f"赚钱原因：{trade.symbol} 次要因素细分可参考归因报告"
            elif pnl < 0:
                key_lesson = f"亏钱原因：{trade.symbol} 需检查入场时机与止损设置，避免追高/撑仓"
            else:
                key_lesson = f"{trade.symbol} 平仓无盈亏，保持当前策略观察"

            summary = (
                f"{trade.symbol} {trade.direction} 以 {trade.entry_price} 入场，"
                f"持仓 {holding_days} 天，"
                f"盈亏 {pnl_pct:+.2f}% ({pnl:+.2f})"
            )

            attribution = None
            try:
                attribution = self._attribution.build_report(
                    strategy_name=trade.strategy_id,
                    period=f"{holding_days}d",
                    positions=[{"symbol": trade.symbol, "return_pct": pnl_pct}],
                    symbol=trade.symbol,
                )
            except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as exc:
                logger.debug("Attribution generation skipped: %s", exc)

            return TradeReviewCard(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                direction=trade.direction,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
                holding_days=holding_days,
                attribution=attribution,
                summary=summary,
                key_lesson=key_lesson,
            )
        except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as exc:
            logger.warning("Review generation failed: %s", exc)
            return TradeReviewCard(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                direction=trade.direction,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                pnl=trade.pnl,
                pnl_pct=trade.pnl_pct,
                holding_days=0,
                summary="复盘生成失败",
                key_lesson="",
            )


_review_service: TradeOutcomeReviewService | None = None
_review_lock = threading.Lock()


def get_trade_review_service() -> TradeOutcomeReviewService:
    global _review_service
    if _review_service is None:
        with _review_lock:
            if _review_service is None:
                _review_service = TradeOutcomeReviewService()
    return _review_service


__all__ = [
    "TradeOutcomeReviewService",
    "TradeRecord",
    "TradeReviewCard",
    "get_trade_review_service",
]
