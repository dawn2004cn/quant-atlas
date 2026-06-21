from __future__ import annotations
"""Domain entities for payment orchestration (Hyperswitch port)."""


import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PaymentStatus(Enum):
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RefundStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GatewayConfig:
    id: int | None = None
    gateway_name: str = ""
    api_key_hash: str = ""
    config_json: str = "{}"
    is_active: bool = True
    priority: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def config(self) -> dict:
        try:
            return json.loads(self.config_json)
        except (json.JSONDecodeError, TypeError):
            return {}


@dataclass
class PaymentIntent:
    intent_id: str
    amount: float
    currency: str
    status: PaymentStatus
    gateway_id: int | None = None
    external_id: str | None = None
    customer_id: str | None = None
    metadata: dict = field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Refund:
    refund_id: str
    intent_id: str
    amount: float
    status: RefundStatus
    external_refund_id: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
