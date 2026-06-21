"""Structured pre-trade gate for UI preview before order submission."""

from __future__ import annotations

from app.core.logger import get_logger
from app.domain.dto.analytics_dto import (
    PositionSizingDTO,
    PreTradeIssueDTO,
    PreTradePreflightDTO,
    RiskConfigDTO,
)
from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.infrastructure.trading.pre_trade_validator import PreTradeValidator

logger = get_logger(__name__)


class PreTradePreflightService:
    """Wrap PreTradeValidator with UI-friendly structured output.

    Enhanced with ATR-based position sizing (plan 2.3 / E-1).
    """

    def __init__(self, *, validator=None, market_service=None):
        self._validator = validator or PreTradeValidator()
        self._market_service = market_service

    def preflight(
        self,
        *,
        symbol,
        direction,
        price,
        quantity,
        strategy_id="manual",
        account_equity=0.0,
        risk_per_trade=0.02,
        sector="unknown",
        portfolio_value=0.0,
        current_position_pct=0.0,
        current_sector_pct=0.0,
    ):
        sym = symbol.strip().upper()
        dir_raw = direction.strip().upper()
        try:
            sig_dir = SignalDirection(dir_raw)
        except ValueError:
            sig_dir = SignalDirection.BUY if dir_raw in ("BUY", "LONG", "B") else SignalDirection.SELL
        signal = TradeSignalDTO(
            symbol=sym,
            direction=sig_dir,
            price=float(price or 0),
            quantity=max(0, int(quantity or 0)),
            strategy_id=strategy_id or "manual",
        )
        risk = RiskConfigDTO(
            account_equity=float(account_equity or 0),
            risk_per_trade=float(risk_per_trade or 0.02),
            max_trade_amount=float(self._validator.max_trade_amount),
            portfolio_value=float(portfolio_value or account_equity or self._validator.max_trade_amount),
            current_position_pct=float(current_position_pct or 0),
            current_sector_pct=float(current_sector_pct or 0),
            sector=sector or "unknown",
        )
        trade_amount = signal.price * signal.quantity
        issues = self._collect_issues(signal, trade_amount, risk)
        sizing = self._compute_position_sizing(sym, float(price or 0), risk)

        validation = self._validator.validate(signal)
        if not validation:
            for reason in validation.reasons:
                issues.append(
                    PreTradeIssueDTO(code="pre_trade_validator", message=reason, severity="blocking")
                )

        blocking = sum(1 for i in issues if i.severity == "blocking")
        warning = sum(1 for i in issues if i.severity == "warning")
        risk_score = max(0, min(100, 92 - blocking * 35 - warning * 12))
        passed = bool(validation) and not any(i.severity == "blocking" for i in issues)
        hints = self._build_hints(passed, warning, sizing.suggested_quantity, quantity)
        review_id = self._maybe_enqueue_review(sym, passed, risk_score, blocking)
        return PreTradePreflightDTO(
            passed=passed,
            allow_execute=passed,
            risk_score=risk_score,
            trade_amount=round(trade_amount, 2),
            max_trade_amount=risk.max_trade_amount,
            issues=issues,
            hints=hints,
            suggested_quantity=sizing.suggested_quantity,
            atr_value=sizing.atr_value,
            suggested_stop_loss=sizing.suggested_stop_loss,
            suggested_take_profit=sizing.suggested_take_profit,
            max_expected_loss=sizing.max_expected_loss,
            risk_per_trade_pct=sizing.risk_per_trade_pct,
            review_queued=bool(review_id),
            review_decision_id=review_id,
        )

    def _maybe_enqueue_review(
        self,
        symbol: str,
        passed: bool,
        risk_score: int,
        blocking: int,
    ) -> str:
        if passed and risk_score >= 45:
            return ""
        try:
            import uuid

            from app.modules.system.services.ui.decision_review_queue import (
                ReviewPriority,
                get_review_queue,
            )

            decision_id = f"preflight_{symbol}_{uuid.uuid4().hex[:8]}"
            priority = (
                ReviewPriority.HIGH.value
                if not passed or blocking > 0
                else ReviewPriority.NORMAL.value
            )
            reason = "preflight_blocked" if not passed else "preflight_low_risk_score"
            get_review_queue().enqueue(
                decision_id=decision_id,
                subject=f"CN:{symbol}",
                confidence=max(0.0, min(1.0, risk_score / 100.0)),
                reason=reason,
                priority=priority,
            )
            return decision_id
        except Exception:
            logger.warning("decision review enqueue skipped", exc_info=True)
            return ""

    def _collect_issues(
        self,
        signal: TradeSignalDTO,
        trade_amount: float,
        risk: RiskConfigDTO,
    ) -> list[PreTradeIssueDTO]:
        issues: list[PreTradeIssueDTO] = []
        sym = signal.symbol
        if not sym:
            issues.append(PreTradeIssueDTO(code="symbol_required", message="code empty", severity="blocking"))
        if signal.quantity <= 0:
            issues.append(PreTradeIssueDTO(code="quantity_invalid", message="quantity must > 0", severity="blocking"))
        if signal.price <= 0:
            issues.append(PreTradeIssueDTO(code="price_invalid", message="price must > 0", severity="blocking"))
        if trade_amount > risk.max_trade_amount:
            issues.append(
                PreTradeIssueDTO(
                    code="trade_amount_exceeds_limit",
                    message=f"amount {trade_amount:.0f} exceeds limit {risk.max_trade_amount:.0f}",
                    severity="blocking",
                )
            )
        elif trade_amount > risk.max_trade_amount * 0.8:
            issues.append(
                PreTradeIssueDTO(
                    code="trade_amount_near_limit",
                    message=f"amount {trade_amount:.0f} near limit {risk.max_trade_amount:.0f}",
                    severity="warning",
                )
            )
        if risk.portfolio_value > 0 and sym:
            try:
                from app.modules.portfolio_risk.services.fund_tier_service import ComplianceGuardrailService

                compliance = ComplianceGuardrailService().check_order(
                    symbol=sym,
                    sector=risk.sector,
                    order_value=trade_amount,
                    portfolio_value=risk.portfolio_value,
                    current_position_pct=risk.current_position_pct,
                    current_sector_pct=risk.current_sector_pct,
                )
                for violation in compliance.violations:
                    issues.append(
                        PreTradeIssueDTO(code="compliance_violation", message=violation, severity="blocking")
                    )
            except (ImportError, RuntimeError, ValueError, TypeError, AttributeError):
                logger.warning("Compliance preflight skipped", exc_info=True)
        return issues

    def _compute_position_sizing(self, symbol: str, entry_price: float, risk: RiskConfigDTO) -> PositionSizingDTO:
        atr = self._compute_atr(symbol)
        return PositionSizingDTO.from_atr(
            entry_price=entry_price,
            atr=atr,
            account_equity=risk.account_equity,
            risk_per_trade=risk.risk_per_trade,
        )

    @staticmethod
    def _build_hints(passed: bool, warning: int, suggested_qty: int, quantity: int) -> list[str]:
        hints: list[str] = []
        if not passed:
            hints.append("adjust quantity/price or split order")
        if warning and passed:
            hints.append("reduce position or review strategy")
        if passed and not warning:
            hints.append("preflight passed, verify in sim first")
        if suggested_qty > 0 and suggested_qty != quantity:
            hints.append(f"ATR suggests {suggested_qty} shares to keep risk under 2%")
        return hints

    @staticmethod
    def _compute_atr_from_bars(bars):
        if not bars or len(bars) < 15:
            return 0.0
        import pandas as pd

        from app.core.risk_controls import compute_atr

        frame = pd.DataFrame(
            [
                {
                    "High": float(bar.get("high") or bar.get("close") or bar.get("price") or 0),
                    "Low": float(bar.get("low") or bar.get("close") or bar.get("price") or 0),
                    "Close": float(bar.get("close") or bar.get("price") or 0),
                }
                for bar in bars
            ]
        )
        atr = compute_atr(frame, window=14)
        if atr.empty:
            return 0.0
        last = float(atr.iloc[-1])
        return round(last, 4) if pd.notna(last) else 0.0

    def _compute_atr(self, symbol):
        ms = getattr(self, "_market_service", None)
        if ms is None or not hasattr(ms, "get_history"):
            return 0.0
        try:
            bars = ms.get_history(symbol, 1, start="", end="")
            if isinstance(bars, list) and len(bars) >= 15:
                return self._compute_atr_from_bars(bars)
            return 0.0
        except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError):
            logger.warning("ATR history fetch failed for %s", symbol, exc_info=True)
            return 0.0
