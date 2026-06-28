from __future__ import annotations
"""Application service for payment orchestration (Hyperswitch port)."""


import uuid

from app.domain.ports import PaymentRepository, PaymentGatewayPort
from app.domain.payment_entities import PaymentIntent, Refund, PaymentStatus, RefundStatus


from app.core.logger import get_logger

logger = get_logger(__name__)


class PaymentOrchestrator:
    def __init__(
        self,
        repository: PaymentRepository,
        gateway_factory: callable  # Function mapping gateway_name to PaymentGatewayPort
    ):
        self._repository = repository
        self._gateway_factory = gateway_factory

    def create_intent(self, amount: float, currency: str, customer_id: str | None = None, metadata: dict | None = None) -> PaymentIntent:
        intent = PaymentIntent(
            intent_id=f"pay_{uuid.uuid4().hex[:12]}",
            amount=amount,
            currency=currency,
            status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
            customer_id=customer_id,
            metadata=metadata or {}
        )
        self._repository.save_payment_intent(intent)
        return intent

    def confirm_payment(self, intent_id: str) -> PaymentIntent:
        intent = self._repository.get_payment_intent(intent_id)
        if not intent:
            raise ValueError(f"Payment intent {intent_id} not found.")

        # Routing Logic: Find the best active gateway
        gateways = self._repository.list_gateways(only_active=True)
        if not gateways:
            raise RuntimeError("No active payment gateways available.")

        # Pick the highest priority gateway
        selected_gateway = gateways[0]
        intent.gateway_id = selected_gateway.id

        gateway_adapter: PaymentGatewayPort = self._gateway_factory(selected_gateway.gateway_name)

        try:
            # Step 1: Create in external gateway
            intent = gateway_adapter.create_payment(intent, selected_gateway)
            # Step 2: Auto-capture if possible (Hyperswitch often supports this)
            if intent.status == PaymentStatus.REQUIRES_CONFIRMATION:
                intent = gateway_adapter.capture_payment(intent, selected_gateway)

            self._repository.save_payment_intent(intent)
        except Exception as e:
            logger.exception("Payment confirmation failed")
            intent.status = PaymentStatus.FAILED
            intent.error_message = str(e)
            self._repository.save_payment_intent(intent)

        return intent

    def refund(self, intent_id: str, amount: float | None = None) -> Refund:
        intent = self._repository.get_payment_intent(intent_id)
        if not intent or intent.status != PaymentStatus.SUCCEEDED:
            raise ValueError(f"Cannot refund intent {intent_id} (Status: {intent.status if intent else 'None'})")

        refund_amount = amount if amount is not None else intent.amount
        refund = Refund(
            refund_id=f"ref_{uuid.uuid4().hex[:12]}",
            intent_id=intent_id,
            amount=refund_amount,
            status=RefundStatus.PENDING
        )

        # Find the gateway used for the original payment
        gateways = self._repository.list_gateways(only_active=False)
        gateway_config = next((g for g in gateways if g.id == intent.gateway_id), None)

        if not gateway_config:
            raise RuntimeError(f"Gateway configuration for ID {intent.gateway_id} not found.")

        gateway_adapter: PaymentGatewayPort = self._gateway_factory(gateway_config.gateway_name)

        try:
            refund = gateway_adapter.refund_payment(refund, intent, gateway_config)
            self._repository.save_refund(refund)
        except Exception as e:
            logger.exception("Refund failed")
            refund.status = RefundStatus.FAILED
            refund.error_message = str(e)
            self._repository.save_refund(refund)

        return refund
