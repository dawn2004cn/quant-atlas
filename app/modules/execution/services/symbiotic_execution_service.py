"""Symbiotic Execution Mesh — Phase 16.
AI-based smart order splitting and sentiment-based cool-down confirmation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.domain.mesh.borderless_schema import (
    SplitOrder, SymbioticExecutionRequest, SymbioticExecutionResult,
    CoolDownReason,
)
from app.domain.monitoring.execution_profile import ExecutionProfile
from app.domain.monitoring.price_tracer import MarketDepthSnapshot
from app.core.logger import get_logger
from app.modules.system.services.risk.risk_companion_service import RiskCompanionService
from app.domain.risk.risk_companion_models import SentimentProfile

logger = get_logger(__name__)


SentimentTrigger = Literal["revenge", "euphoric", "fear", "panic"]


class SymbioticExecutionService:
    """Smart order splitting and sentiment-triggered cool-down."""

    def __init__(
        self,
        *,
        risk_companion: RiskCompanionService,
        book_service: Any,
        execution_profiler: Any | None = None,
    ):
        self._risk = risk_companion
        self._book = book_service
        self._profiler = execution_profiler
        self._sentiment_cache: dict[int, SentimentProfile] = {}
    
    def parse_sentiment(self, user_id: int) -> SentimentProfile:
        """Get or infer user sentiment."""
        cached = self._sentiment_cache.get(user_id)
        if cached:
            # Refresh if older than 30 minutes
            age = datetime.now(timezone.utc) - cached.assessed_at
            if age.total_seconds() < 1800:
                return cached
        fresh = self._risk.assess_user_risk_profile(user_id)
        self._sentiment_cache[user_id] = fresh
        return fresh
    
    def detect_triggers(self, profile: SentimentProfile) -> list[SentimentTrigger]:
        """Detect emotion triggers."""
        triggers = []
        if profile.recent_loss_count > 3 and profile.win_rate_24h < 0.3:
            triggers.append("revenge")
        if profile.win_rate_24h > 0.8 and profile.trade_frequency > 9:
            triggers.append("euphoric")
        if profile.trade_size_avg > profile.normal_trade_size * 2:
            triggers.append("panic")
        if profile.position_volatility > 0.3:
            triggers.append("fear")
        return triggers
    
    def calculate_split(self, req: SymbioticExecutionRequest, depth: MarketDepthSnapshot) -> list[SplitOrder]:
        """Split single large order into smaller hidden child orders."""
        splits = []
        remaining = req.quantity
        spread = depth.ask - depth.bid
        book_balance = math.sqrt((depth.bid_size + depth.ask_size) / 2)
        
        split_size = max(5, min(req.quantity // 5, book_balance * 0.25))
        while remaining > split_size:
            splits.append(SplitOrder(
                order_id=f"child-{req.symbol}-{len(splits)}",
                quantity=split_size,
                price=None,  # market order
                hidden=True,
                delay_ms=max(250, min(1200, spread ** 2 * 1000)),
            ))
            remaining -= split_size
            split_size *= 1.1  # increase subsequent child order size
        
        if remaining > 0:
            splits.append(SplitOrder(
                order_id=f"child-{req.symbol}-{len(splits)}",
                quantity=remaining,
                price=None,
                hidden=True,
                delay_ms=100,
            ))
        return splits
    
    def symbiotic_execute(self, req: SymbioticExecutionRequest) -> SymbioticExecutionResult:
        """Main symbiotic execution entry."""
        profile = self.parse_sentiment(req.user_id)
        triggers = self.detect_triggers(profile)
        
        # --- Cool-down intervention ----------------------------------------------
        cool_down = None
        if triggers:
            reason = CoolDownReason.REVENGE_TRADING if "revenge" in triggers else CoolDownReason.SENTIMENT_TILT
            cool_down = self._request_cool_down(req.user_id, profile, triggers)
        if cool_down:
            return SymbioticExecutionResult(
                ok=False,
                error=f"Cool-down: {' '.join(triggers)}",
                cool_down_reason=reason,
                suggested_delay_seconds=cool_down.suggested_delay,
                sentiment_triggers=triggers,
            )
        
        # --- Smart order splitting ----------------------------------------------
        try:
            depth = None
            if hasattr(self._book, 'get_depth'):
                depth = self._book.get_depth(req.symbol, req.market)
            if not depth:
                depth = MarketDepthSnapshot(
                    bid=req.price or 0,
                    ask=(req.price or 0) + (0.01 if req.market == 'CN' else 0.001),
                    bid_size=100,
                    ask_size=100,
                )
            
            splits = self.calculate_split(req, depth)
            if not splits:
                return SymbioticExecutionResult(
                    ok=False,
                    error="Empty splits",
                )
            
            # --- Dispatch ---------------------------------------------------------
            dispatched = []
            for split_req in splits:
                success = self._dispatch_child_order(split_req, req.user_id, req.strategy_id)
                dispatched.append(success)
            
            return SymbioticExecutionResult(
                ok=True,
                splits=[
                    {
                        "order_id": s.order_id,
                        "quantity": s.quantity,
                        "price": s.price or "market",
                        "status": "sent",
                    }
                    for s, stat in zip(splits, dispatched) if stat
                ],
                child_count=len([1 for d in dispatched if d]),
            )
        
        except Exception as exc:
            logger.warning("Symbiotic execute failed for %s: %s", req.symbol, exc)
            return SymbioticExecutionResult(
                ok=False,
                error=str(exc),
            )
    
    def _request_cool_down(
        self, user_id: int, profile: SentimentProfile, triggers: list[SentimentTrigger]
    ) -> Any | None:
        """Request cool-down intervention."""
        narrative = self._risk.format_sentiment_warning(profile, triggers)
        if self._risk.should_intervene(user_id, narrative):
            delay = 3 if "revenge" in triggers else 6
            max_delay = 12
            return {
                "user_id": user_id,
                "reason": triggers,
                "suggested_delay": min(max_delay, max(delay, profile.tilt_duration_sec)),
                "intervention_message": narrative,
            }
        return None
    
    def _dispatch_child_order(self, order: SplitOrder, user_id: int, strategy_id: str | None) -> bool:
        """Dispatch child order to execution module."""
        try:
            if not self._profiler:
                logger.warning("No profiler set - skipping child order %s", order.order_id)
                return False
            trace = ExecutionProfile(
                order_id=order.order_id,
                symbol=order.order_id.split('-')[1],
                quantity=order.quantity,
                price=order.price,
                user_id=user_id,
                strategy_id=strategy_id or "manual",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            # Push to execution profiler;
            self._profiler.record_order(trace.route_by())
            # Route to execution engine via message queue;
            bus = self._profiler.event_bus
            bus.publish("ORDER_SPLIT", payload={
                "user_id": user_id,
                "symbol": trace.symbol,
                "quantity": order.quantity,
                "price": order.price,
                "hidden": order.hidden,
                "delay_ms": order.delay_ms,
            })
            return True
        except Exception as exc:
            logger.warning("Child order dispatch failed: %s", exc)
            return False


__all__ = ["SymbioticExecutionService"]
