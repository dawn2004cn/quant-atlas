from __future__ import annotations

"""Port for pre-trade signal validation."""

from typing import Protocol

from app.domain.dto.trade_signal_dto import TradeSignalDTO


class PreTradeValidationPort(Protocol):
    def validate(self, signal: TradeSignalDTO) -> bool:
        ...
