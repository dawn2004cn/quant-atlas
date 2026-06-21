"""Pre-trade risk validation logic."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logger import get_logger
from app.domain.dto.trade_signal_dto import TradeSignalDTO

logger = get_logger(__name__)


@dataclass(frozen=True)
class ValidationResult:
    """Structured result from PreTradeValidator.validate().

    Backward compatible: ``bool(result)`` returns ``passed``.
    """

    passed: bool
    reasons: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.passed


class InMemorySettlementTracker:
    """Track same-day BUY fills so SELL can be blocked under T+1 rules.

    This is a minimal process-local tracker. A production deployment should
    persist settlement state to Redis or the ledger database.
    """

    def __init__(self):
        self._buys: dict[str, set[str]] = {}

    def record_buy(self, symbol: str, trade_date: str | None = None) -> None:
        trade_date = trade_date or self._today()
        self._buys.setdefault(symbol, set()).add(trade_date)

    def can_sell(self, symbol: str, trade_date: str | None = None) -> bool:
        """A-share T+1: cannot sell shares bought on the same trading day."""
        trade_date = trade_date or self._today()
        return trade_date not in self._buys.get(symbol, set())

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")


class PreTradeValidator:
    """Mandatory risk checks before any trade execution."""

    def __init__(
        self,
        max_trade_amount: float = 1000000.0,
        max_position_per_stock: int = 0,
        get_position_size: object | None = None,
        market_provider: object | None = None,
        settlement_tracker: InMemorySettlementTracker | None = None,
        get_account_equity: Callable[[], float] | None = None,
    ):
        self.max_trade_amount = max_trade_amount
        self.max_position_per_stock = max_position_per_stock
        self._get_position_size = get_position_size
        self._market_provider = market_provider
        self._settlement_tracker = settlement_tracker or InMemorySettlementTracker()
        self._get_account_equity = get_account_equity

    def validate(self, signal: TradeSignalDTO) -> ValidationResult:
        """Perform hard checks before execution.

        Returns a ValidationResult. ``bool(result)`` works as before.
        """
        reasons: list[str] = []
        trade_amount = signal.price * signal.quantity

        if trade_amount > self.max_trade_amount:
            reasons.append(
                f"Order value {trade_amount:.2f} exceeds max_trade_amount {self.max_trade_amount:.2f}"
            )

        side = (signal.direction.value or "").upper()
        symbol = (signal.symbol or "").upper()

        # Position limit check (only on BUY).
        if self.max_position_per_stock > 0 and side == "BUY":
            current_qty = 0
            if self._get_position_size is not None:
                try:
                    current_qty = int(self._get_position_size(symbol))
                except Exception:
                    current_qty = 0
            new_total = current_qty + signal.quantity
            if new_total > self.max_position_per_stock:
                reasons.append(
                    f"BUY {signal.quantity} would exceed position limit "
                    f"{self.max_position_per_stock} (current {current_qty})"
                )

        # T+1 settlement check for A-share SELL.
        if side == "SELL" and self._is_cn_symbol(symbol):
            if not self._settlement_tracker.can_sell(symbol):
                reasons.append(f"T+1 settlement blocks same-day SELL for {symbol}")

        # A-share price limit check.
        if self._is_cn_symbol(symbol) and self._market_provider is not None:
            limit_reason = self._check_cn_price_limit(symbol, signal.price, side)
            if limit_reason:
                reasons.append(limit_reason)

        # Available fund check on BUY.
        if side == "BUY" and self._get_account_equity is not None:
            try:
                equity = float(self._get_account_equity())
                if equity < trade_amount:
                    reasons.append(
                        f"Insufficient equity {equity:.2f} for order value {trade_amount:.2f}"
                    )
            except Exception:
                logger.warning("Account equity check failed", exc_info=True)

        if reasons:
            for reason in reasons:
                logger.error("PreTrade Risk Alert: %s (%s)", reason, symbol)
            return ValidationResult(passed=False, reasons=reasons)
        return ValidationResult(passed=True)

    @staticmethod
    def _is_cn_symbol(symbol: str) -> bool:
        from app.infrastructure.providers.cn_backtest_rules import is_cn_symbol as _is_cn

        return _is_cn(symbol)

    def _check_cn_price_limit(
        self, symbol: str, price: float, side: str
    ) -> str | None:
        """Return a reason string if the order price violates A-share limits."""
        try:
            quote = self._market_provider.get_realtime_quotes(symbol)
            if not quote:
                return None
            if isinstance(quote, list):
                quote = quote[0]
            if not isinstance(quote, dict):
                return None

            prev_close = quote.get("prev_close") or quote.get("pre_close") or quote.get("close")
            if prev_close is None:
                return None
            prev_close = float(prev_close)
            if prev_close <= 0:
                return None

            from app.infrastructure.providers.cn_backtest_rules import cn_limit_threshold

            thr = cn_limit_threshold(symbol)
            upper = prev_close * (1.0 + thr)
            lower = prev_close * (1.0 - thr)
            eps = prev_close * 0.0005

            side_u = side.upper()
            if side_u == "BUY" and price > upper + eps:
                return f"BUY price {price:.3f} exceeds limit-up {upper:.3f}"
            if side_u == "SELL" and price < lower - eps:
                return f"SELL price {price:.3f} below limit-down {lower:.3f}"
        except Exception:
            logger.warning("Price limit check skipped for %s", symbol, exc_info=True)
        return None
