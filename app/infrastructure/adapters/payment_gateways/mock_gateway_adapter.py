from __future__ import annotations
"""Mock implementation of PaymentGatewayPort for demonstration."""


import uuid
from app.domain.ports import PaymentGatewayPort
from app.domain.payment_entities import PaymentIntent, Refund, GatewayConfig, PaymentStatus, RefundStatus


class MockPaymentGatewayAdapter(PaymentGatewayPort):
    def create_payment(self, intent: PaymentIntent, config: GatewayConfig) -> PaymentIntent:
        # Simulate external gateway call
        intent.external_id = f"mock_pi_{uuid.uuid4().hex[:8]}"
        intent.status = PaymentStatus.REQUIRES_CONFIRMATION
        return intent

    def capture_payment(self, intent: PaymentIntent, config: GatewayConfig) -> PaymentIntent:
        # Simulate successful capture
        intent.status = PaymentStatus.SUCCEEDED
        return intent

    def refund_payment(self, refund: Refund, intent: PaymentIntent, config: GatewayConfig) -> Refund:
        # Simulate successful refund
        refund.external_refund_id = f"mock_re_{uuid.uuid4().hex[:8]}"
        refund.status = RefundStatus.SUCCEEDED
        return refund
