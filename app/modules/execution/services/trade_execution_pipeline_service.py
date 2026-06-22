"""Unified trade execution pipeline — Phase II/III integration.

Fast Path chain: Compliance Guardrail → Pre-Trade Validation → Audit Snapshot → Execute.
Slow Path: AI evidence indexing (async observer).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.infrastructure.trading.gateway_client import TradeExecutionStub
from app.infrastructure.trading.pre_trade_validator import PreTradeValidator

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:  # pragma: no cover
    SQLAlchemyError = RuntimeError  # type: ignore[misc,assignment]

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Result of a full trade execution pipeline run."""

    ok: bool
    order_id: str = ""
    snapshot_id: str = ""
    stage: str = "completed"
    compliance: dict[str, Any] = field(default_factory=dict)
    pre_trade: dict[str, Any] = field(default_factory=dict)
    impact: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TradeExecutionPipelineService:
    """Industrial trade pipeline: compliance → risk → audit → execution.

    Compliance is **mandatory** — there is no skip.  RBAC can be bypassed
    via ``skip_rbac`` for internal calls (e.g. master-slave mirroring).
    """

    _LARGE_ORDER_USD = 500_000.0

    def __init__(
        self,
        compliance_guardrail: Any | None = None,
        audit_trail: Any | None = None,
        impact_model: Any | None = None,
        validator: PreTradeValidator | None = None,
        gateway: TradeExecutionStub | None = None,
        compliance_session: Any | None = None,
        audit_session: Any | None = None,
    ):
        self._compliance = compliance_guardrail
        self._audit = audit_trail
        self._impact = impact_model
        self._gateway = gateway or TradeExecutionStub(
            use_grpc=bool(os.environ.get("TRADE_GATEWAY_GRPC")),
            grpc_target=os.environ.get("TRADE_GATEWAY_TARGET", "localhost:9090"),
        )
        self._validator = validator or PreTradeValidator()
        self._compliance_session = compliance_session
        self._audit_session = audit_session

    def _pre_trade_check(self, signal: TradeSignalDTO, order_id: str) -> dict:
        """Validate via gateway (gRPC) if available, else local fallback."""
        resp = self._gateway.submit_order(
            order_id=order_id,
            symbol=signal.symbol,
            side=signal.direction.value,
            price=signal.price,
            quantity=signal.quantity,
            strategy_id=signal.strategy_id,
            user_id=str(signal.user_id or ""),
            dry_run=True,
            local_fallback=self._validator,
        )
        return {"valid": resp.accepted, "reason": resp.reason, "gateway": resp.gateway_version}

    def _get_compliance(self) -> Any:
        if self._compliance is None:
            from app.modules.portfolio_risk.services.fund_tier_service import ComplianceGuardrailService

            self._compliance = ComplianceGuardrailService(session=self._compliance_session)
        return self._compliance

    def _get_audit(self) -> Any:
        if self._audit is None:
            from app.modules.portfolio_risk.services.fund_tier_service import AuditTrailService

            self._audit = AuditTrailService(session=self._audit_session)
        return self._audit

    def _get_impact(self) -> Any:
        if self._impact is None:
            from app.modules.system.services.institution_tier_service import MarketImpactModelService

            self._impact = MarketImpactModelService()
        return self._impact

    def execute(
        self,
        *,
        user_id: int,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        sector: str = "unknown",
        portfolio_value: float = 1_000_000.0,
        current_position_pct: float = 0.0,
        current_sector_pct: float = 0.0,
        strategy_id: str = "pipeline",
        ai_evidence: dict | None = None,
        factor_values: dict | None = None,
        skip_impact: bool = False,
        skip_rbac: bool = False,
    ) -> PipelineResult:
        """Run full Fast Path pipeline; block on any compliance/risk failure."""
        # ── RBAC ────────────────────────────────────────────────────
        if not skip_rbac:
            try:
                from app.modules.system.services.institution_tier_service import RBACService

                rbac = RBACService()
                rbac.require_permission(user_id, "order", "execute")
            except (PermissionError, RuntimeError):
                return PipelineResult(
                    ok=False,
                    stage="rbac",
                    violations=["RBAC check failed — order execution not authorized"],
                )

        sym = symbol.strip().upper()
        order_value = price * quantity
        order_id = f"ord.{uuid.uuid4().hex[:10]}"

        # ── Compliance (mandatory — no skip) ────────────────────────
        compliance = self._get_compliance().check_order(
            symbol=sym,
            sector=sector,
            order_value=order_value,
            portfolio_value=max(portfolio_value, 1.0),
            current_position_pct=current_position_pct,
            current_sector_pct=current_sector_pct,
        )

        if not compliance.passed:
            # Log violation to DB
            self._log_compliance_violation(order_id, user_id, sym, compliance.violations)
            return PipelineResult(
                ok=False,
                order_id=order_id,
                stage="compliance",
                compliance=compliance.__dict__,
                violations=compliance.violations,
            )

        # ── Pre-trade validation (gateway + local fallback) ──────────
        direction = SignalDirection.BUY if action.lower() in ("buy", "long") else SignalDirection.SELL
        signal = TradeSignalDTO(
            symbol=sym,
            direction=direction,
            price=float(price),
            quantity=int(quantity),
            strategy_id=strategy_id,
            user_id=user_id,
        )
        pre_trade = self._pre_trade_check(signal, order_id)
        if not pre_trade["valid"]:
            return PipelineResult(
                ok=False,
                order_id=order_id,
                stage="pre_trade",
                compliance=compliance.__dict__,
                pre_trade=pre_trade,
                violations=[pre_trade.get("reason", "Pre-trade risk validation failed")],
            )

        # ── Market impact (optional) ────────────────────────────────
        impact_data: dict[str, Any] = {}
        if not skip_impact and order_value >= self._LARGE_ORDER_USD:
            forecast = self._get_impact().forecast(sym, order_value, side=action.lower())
            impact_data = forecast.__dict__
            if forecast.estimated_impact_bps > 80:
                return PipelineResult(
                    ok=False,
                    order_id=order_id,
                    stage="impact",
                    compliance=compliance.__dict__,
                    pre_trade=pre_trade,
                    impact=impact_data,
                    violations=[f"Estimated impact {forecast.estimated_impact_bps:.0f}bps exceeds threshold"],
                )

        # ── Audit snapshot ──────────────────────────────────────────
        snapshot = self._get_audit().record_snapshot(
            order_id=order_id,
            user_id=user_id,
            symbol=sym,
            action=action,
            quantity=quantity,
            price=price,
            ai_evidence=ai_evidence,
            factor_values=factor_values,
            risk_assessment=pre_trade,
            compliance_result=compliance.__dict__,
        )

        execution = {
            "symbol": sym,
            "action": action,
            "quantity": quantity,
            "price": price,
            "value": round(order_value, 2),
            "status": "accepted",
        }
        # Record BUY for T+1 settlement tracking (A-share)
        if direction == SignalDirection.BUY and self._is_cn_symbol(sym):
            self._validator._settlement_tracker.record_buy(sym)

        logger.info(
            "Trade pipeline OK: order=%s user=%d %s %d %s",
            order_id,
            user_id,
            action,
            quantity,
            sym,
        )
        return PipelineResult(
            ok=True,
            order_id=order_id,
            snapshot_id=snapshot.snapshot_id,
            compliance=compliance.__dict__,
            pre_trade=pre_trade,
            impact=impact_data,
            execution=execution,
        )

    def _log_compliance_violation(self, order_id: str, user_id: int,
                                   symbol: str, violations: list[str]) -> None:
        """Write compliance violations to the DB violation log."""
        session = self._audit_session
        if session is None:
            return
        try:
            from app.infrastructure.database.models import ComplianceViolationLog

            for detail in violations:
                violation = ComplianceViolationLog(
                    order_id=order_id,
                    user_id=user_id,
                    symbol=symbol,
                    violation_detail=detail,
                )
                session.add(violation)
            session.flush()
        except (SQLAlchemyError, OSError, RuntimeError, ValueError, TypeError):
            logger.exception("Failed to log compliance violation for order %s", order_id)


    @staticmethod
    def _is_cn_symbol(symbol: str) -> bool:
        """Check if symbol is A-share for T+1 settlement rules."""
        from app.infrastructure.providers.cn_backtest_rules import is_cn_symbol as _is_cn
        return _is_cn(symbol.upper())

__all__ = ["TradeExecutionPipelineService", "PipelineResult"]
