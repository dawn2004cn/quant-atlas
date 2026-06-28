from __future__ import annotations

"""Infrastructure adapter for ``PreTradeValidationPort``."""

from app.domain.dto.trade_signal_dto import TradeSignalDTO
from app.domain.ports.pre_trade_validation_port import PreTradeValidationPort
from app.infrastructure.trading.pre_trade_validator import PreTradeValidator


class PreTradeValidationPortAdapter(PreTradeValidationPort):
    def __init__(self, *, max_trade_amount: float = 1_000_000.0) -> None:
        self._validator = PreTradeValidator(max_trade_amount=max_trade_amount)

    def validate(self, signal: TradeSignalDTO) -> bool:
        return self._validator.validate(signal)
