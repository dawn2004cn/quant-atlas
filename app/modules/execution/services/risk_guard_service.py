"""Application Risk Guard: gate orders and trigger flatten/suspend (REQ-SRS-01)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from app.core.logger import get_logger
from app.domain.trading.risk_guard import RiskGuardDecision, evaluate_account_risk

logger = get_logger(__name__)


class RiskGuardBlockedError(PermissionError):
    """Raised when Risk Guard blocks a new order."""

    def __init__(self, decision: RiskGuardDecision) -> None:
        self.decision = decision
        super().__init__(f"risk_guard_blocked:{decision.action}:{decision.reason}")


@dataclass(slots=True)
class AccountRiskSnapshot:
    equity: float
    day_start_equity: float
    consecutive_stop_outs: int = 0
    execution_suspended: bool = False


class RiskGuardStorePort(Protocol):
    def get_snapshot(self, account_id: str) -> AccountRiskSnapshot: ...

    def set_snapshot(self, account_id: str, snapshot: AccountRiskSnapshot) -> None: ...


class RiskGuardActionsPort(Protocol):
    def flatten_all(self, account_id: str, reason: str) -> None: ...

    def suspend_execution(self, account_id: str, reason: str) -> None: ...

    def alert(self, account_id: str, decision: RiskGuardDecision) -> None: ...


class InMemoryRiskGuardStore:
    """Process-local store for tests and single-process paper trading."""

    def __init__(self) -> None:
        self._rows: dict[str, AccountRiskSnapshot] = {}

    def get_snapshot(self, account_id: str) -> AccountRiskSnapshot:
        row = self._rows.get(account_id)
        if row is None:
            return AccountRiskSnapshot(equity=100_000.0, day_start_equity=100_000.0)
        return row

    def set_snapshot(self, account_id: str, snapshot: AccountRiskSnapshot) -> None:
        self._rows[account_id] = snapshot


class LoggingRiskGuardActions:
    """Default actions: log + optional alerter callback."""

    def __init__(self, alerter: Callable[[str, RiskGuardDecision], None] | None = None) -> None:
        self._alerter = alerter

    def flatten_all(self, account_id: str, reason: str) -> None:
        logger.error("risk_guard flatten_all account=%s reason=%s", account_id, reason)

    def suspend_execution(self, account_id: str, reason: str) -> None:
        logger.error("risk_guard suspend_execution account=%s reason=%s", account_id, reason)

    def alert(self, account_id: str, decision: RiskGuardDecision) -> None:
        logger.warning(
            "risk_guard alert account=%s action=%s reason=%s",
            account_id,
            decision.action,
            decision.reason,
        )
        if self._alerter is not None:
            try:
                self._alerter(account_id, decision)
            except Exception:
                logger.warning("risk_guard alerter failed", exc_info=True)


class RiskGuardService:
    """Hard risk gate independent of AI preflight."""

    def __init__(
        self,
        *,
        store: RiskGuardStorePort | None = None,
        actions: RiskGuardActionsPort | None = None,
        max_daily_drawdown_pct: float = 0.05,
        max_consecutive_stop_outs: int = 3,
    ) -> None:
        self._store = store or InMemoryRiskGuardStore()
        self._actions = actions or LoggingRiskGuardActions()
        self._max_daily_drawdown_pct = max_daily_drawdown_pct
        self._max_consecutive_stop_outs = max_consecutive_stop_outs

    def check_before_order(self, account_id: str) -> RiskGuardDecision:
        snap = self._store.get_snapshot(account_id)
        if snap.execution_suspended:
            return RiskGuardDecision(
                "suspend_execution",
                True,
                "execution_suspended",
            )
        return evaluate_account_risk(
            equity=snap.equity,
            day_start_equity=snap.day_start_equity,
            consecutive_stop_outs=snap.consecutive_stop_outs,
            max_daily_drawdown_pct=self._max_daily_drawdown_pct,
            max_consecutive_stop_outs=self._max_consecutive_stop_outs,
        )

    def on_decision(self, account_id: str, decision: RiskGuardDecision) -> None:
        if decision.action == "allow":
            return
        if decision.action == "flatten_all":
            self._actions.flatten_all(account_id, decision.reason)
        if decision.action in ("flatten_all", "suspend_execution"):
            self._actions.suspend_execution(account_id, decision.reason)
            snap = self._store.get_snapshot(account_id)
            self._store.set_snapshot(
                account_id,
                AccountRiskSnapshot(
                    equity=snap.equity,
                    day_start_equity=snap.day_start_equity,
                    consecutive_stop_outs=snap.consecutive_stop_outs,
                    execution_suspended=True,
                ),
            )
        self._actions.alert(account_id, decision)

    def ensure_order_allowed(self, account_id: str) -> RiskGuardDecision:
        decision = self.check_before_order(account_id)
        if decision.block_new_orders:
            self.on_decision(account_id, decision)
            raise RiskGuardBlockedError(decision)
        return decision

    def record_stop_out(self, account_id: str) -> RiskGuardDecision:
        """Increment consecutive stop-outs and re-evaluate (may suspend)."""
        snap = self._store.get_snapshot(account_id)
        updated = AccountRiskSnapshot(
            equity=snap.equity,
            day_start_equity=snap.day_start_equity,
            consecutive_stop_outs=snap.consecutive_stop_outs + 1,
            execution_suspended=snap.execution_suspended,
        )
        self._store.set_snapshot(account_id, updated)
        decision = self.check_before_order(account_id)
        if decision.block_new_orders:
            self.on_decision(account_id, decision)
        return decision

    def update_equity(self, account_id: str, equity: float, *, day_start_equity: float | None = None) -> None:
        snap = self._store.get_snapshot(account_id)
        self._store.set_snapshot(
            account_id,
            AccountRiskSnapshot(
                equity=equity,
                day_start_equity=snap.day_start_equity if day_start_equity is None else day_start_equity,
                consecutive_stop_outs=snap.consecutive_stop_outs,
                execution_suspended=snap.execution_suspended,
            ),
        )
