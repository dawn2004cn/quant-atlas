"""Audit trail query service — list, search, and verify audit events."""

from __future__ import annotations

from datetime import datetime

from app.core.logger import get_logger
from app.modules.portfolio_risk.services.fund_tier_service import (
    AuditTrailService,
    DecisionSnapshot,
)

logger = get_logger(__name__)


class AuditQueryService:
    """Read-only query layer over audit_events table."""

    def __init__(self, session=None):
        self._session = session

    def list_events(
        self,
        *,
        user_id: int | None = None,
        symbol: str | None = None,
        order_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict:
        """Paginated list of audit events."""
        from app.infrastructure.database.models import AuditEvent

        session = self._session
        if session is None:
            return {"events": [], "total": 0, "page": page, "per_page": per_page}

        query = session.query(AuditEvent)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        if symbol is not None:
            query = query.filter_by(symbol=symbol.upper())
        if order_id is not None:
            query = query.filter_by(order_id=order_id)
        if start is not None:
            query = query.filter(AuditEvent.timestamp >= start)
        if end is not None:
            query = query.filter(AuditEvent.timestamp <= end)

        total = query.count()
        events = (
            query.order_by(AuditEvent.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "events": [
                {
                    "snapshot_id": e.snapshot_id,
                    "order_id": e.order_id,
                    "user_id": e.user_id,
                    "symbol": e.symbol,
                    "action": e.action,
                    "quantity": e.quantity,
                    "price": e.price,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                    "content_hash": e.content_hash,
                    "chain_hash": e.chain_hash,
                }
                for e in events
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def get_event(self, snapshot_id: str) -> DecisionSnapshot | None:
        """Get a single audit event by snapshot_id."""
        from app.infrastructure.database.models import AuditEvent

        session = self._session
        if session is None:
            return None

        event = session.query(AuditEvent).filter_by(snapshot_id=snapshot_id).first()
        if event is None:
            return None

        return DecisionSnapshot(
            snapshot_id=event.snapshot_id,
            order_id=event.order_id,
            user_id=event.user_id,
            symbol=event.symbol,
            action=event.action,
            quantity=event.quantity,
            price=event.price,
            ai_evidence=__import__("json").loads(event.ai_evidence_json) if event.ai_evidence_json else {},
            factor_values=__import__("json").loads(event.factor_values_json) if event.factor_values_json else {},
            risk_assessment=__import__("json").loads(event.risk_assessment_json) if event.risk_assessment_json else {},
            compliance_result=__import__("json").loads(event.compliance_result_json) if event.compliance_result_json else {},
            timestamp=event.timestamp.isoformat() if event.timestamp else "",
            previous_hash=event.previous_hash,
            content_hash=event.content_hash,
            chain_hash=event.chain_hash,
        )

    def verify_order_chain(self, order_id: str):
        """Verify hash chain for an order using the audit trail service."""
        service = AuditTrailService(session=self._session)
        return service.verify_order_chain(order_id)

    def verify_global_chain(self):
        """Verify the full audit chain."""
        service = AuditTrailService(session=self._session)
        return service.verify_global_chain()
