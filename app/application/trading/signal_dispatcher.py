"""Signal Dispatcher for trade execution."""

from typing import Any
from app.core.events import risk_alert_triggered
from app.domain.dto.trade_signal_dto import TradeSignalDTO

from app.domain.ports.execution_ports import ITradeExecutor
from app.domain.ports.pre_trade_validation_port import PreTradeValidationPort


from app.core.logger import get_logger

logger = get_logger(__name__)

class SignalDispatcher:
    """Routes strategy signals to execution gateways with pre-trade checks."""

    def __init__(self, executor: ITradeExecutor, validator: PreTradeValidationPort):
        self._executor = executor
        self._validator = validator
        # Listen to risk alerts as a proof of concept
        risk_alert_triggered.connect(self._handle_risk_alert)

    def _handle_risk_alert(self, sender: Any, **kwargs) -> None:
        """Process signal from events."""
        signal = kwargs.get("signal")
        if isinstance(signal, TradeSignalDTO):
            self.dispatch(signal)

    def dispatch(self, signal: TradeSignalDTO) -> None:
        """Route to execution gateway after validation."""
        if not self._validator.validate(signal):
            logger.warning(f"Trade signal rejected by PreTradeValidator: {signal.symbol}")
            return

        logger.info(f"Dispatching trade signal: {signal.direction} {signal.quantity} shares of {signal.symbol}")
        self._executor.execute(signal)
