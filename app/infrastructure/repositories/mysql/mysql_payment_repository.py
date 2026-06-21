from __future__ import annotations
"""SQLAlchemy payment repository implementation."""


import json
from typing import Any
from sqlalchemy import select, desc

from app.domain.ports import PaymentRepository
from app.domain.payment_entities import PaymentIntent, Refund, GatewayConfig, PaymentStatus, RefundStatus
from app.infrastructure.database.models.trading import GatewayConfig as DBGatewayConfig, PaymentIntent as DBPaymentIntent, PaymentRefund as DBPaymentRefund


class MySQLPaymentRepository(PaymentRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory
    
    def create_payment(self, payment_data: dict) -> dict:
        """Create a new payment."""
        payment_id = payment_data.get("id", "payment_stub")
        return {"id": payment_id, "status": "pending", **payment_data}
    
    def get_payment(self, payment_id: str) -> Any | None:
        """Get payment by ID (stub for interface compatibility)."""
        return None
    
    def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status (stub for interface compatibility)."""
        return True
    
    def save_payment(self, payment: Any) -> str:
        """Save payment (stub for interface compatibility)."""
        if hasattr(payment, 'intent_id'):
            return str(payment.intent_id)
        return "stub_payment_id"

    def save_payment_intent(self, intent: PaymentIntent) -> None:
        session = self._session_factory()
        try:
            db_intent = session.get(DBPaymentIntent, intent.intent_id)
            if not db_intent:
                db_intent = DBPaymentIntent(intent_id=intent.intent_id)
                session.add(db_intent)
            
            db_intent.amount = intent.amount
            db_intent.currency = intent.currency
            db_intent.status = intent.status.value
            db_intent.gateway_id = intent.gateway_id
            db_intent.external_id = intent.external_id
            db_intent.customer_id = intent.customer_id
            db_intent.metadata_json = json.dumps(intent.metadata)
            db_intent.error_message = intent.error_message
            
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_payment_intent(self, intent_id: str) -> PaymentIntent | None:
        session = self._session_factory()
        try:
            db_intent = session.get(DBPaymentIntent, intent_id)
            if not db_intent:
                return None
            return self._map_db_to_intent(db_intent)
        finally:
            session.close()

    def list_gateways(self, only_active: bool = True) -> list[GatewayConfig]:
        session = self._session_factory()
        try:
            stmt = select(DBGatewayConfig)
            if only_active:
                stmt = stmt.where(DBGatewayConfig.is_active == 1)
            stmt = stmt.order_by(desc(DBGatewayConfig.priority))
            rows = session.scalars(stmt).all()
            return [self._map_db_to_gateway(r) for r in rows]
        finally:
            session.close()

    def save_refund(self, refund: Refund) -> None:
        session = self._session_factory()
        try:
            db_refund = session.get(DBPaymentRefund, refund.refund_id)
            if not db_refund:
                db_refund = DBPaymentRefund(refund_id=refund.refund_id)
                session.add(db_refund)
            
            db_refund.intent_id = refund.intent_id
            db_refund.amount = refund.amount
            db_refund.status = refund.status.value
            db_refund.external_refund_id = refund.external_refund_id
            db_refund.error_message = refund.error_message
            
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _map_db_to_intent(self, r: DBPaymentIntent) -> PaymentIntent:
        return PaymentIntent(
            intent_id=r.intent_id,
            amount=r.amount,
            currency=r.currency,
            status=PaymentStatus(r.status),
            gateway_id=r.gateway_id,
            external_id=r.external_id,
            customer_id=r.customer_id,
            metadata=json.loads(r.metadata_json) if r.metadata_json else {},
            error_message=r.error_message,
            created_at=r.created_at,
            updated_at=r.updated_at
        )

    def _map_db_to_gateway(self, r: DBGatewayConfig) -> GatewayConfig:
        return GatewayConfig(
            id=r.id,
            gateway_name=r.gateway_name,
            api_key_hash=r.api_key_hash,
            config_json=r.config_json or "{}",
            is_active=bool(r.is_active),
            priority=r.priority,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
