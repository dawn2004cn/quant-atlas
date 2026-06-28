"""Trading workflow — signal generation, risk check, order execution.

This workflow wires three domain services into an end-to-end pipeline:

1. **Signal generation** — fetches bars via CapabilityRegistry, computes
   technical indicators, and produces a ``GeneratedSignal`` using
   ``SignalGenerationService``.
2. **Risk check** — validates the signal against ``TradingPolicyService``
   (position limits, market hours, circuit breaker).
3. **Order execution** — submits a simulated or live order via the
   capability registry, emitting a ``TradeExecutedEvent`` for audit
   lineage.

Usage::

    wf = TradingWorkflow(
        workflow_id="wf_abc123",
        symbol="600519",
        market=MarketCode.CN,
        strategy_name="golden_cross",
        capability_registry=registry,
    )
    wf.start()
"""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from app.core.event_bus import TradeExecutedEvent, get_event_bus
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.services.signal_generation_service import (
    SignalAggregator,
    SignalConfig,
    SignalGenerationService,
    SignalSource,
)
from app.domain.services.trading_policy_service import (
    PolicyResult,
    TradingPolicy,
    TradingPolicyService,
)

from .base_workflow import BaseWorkflow


def _CapabilityRegistry():
    """Lazy import via factory to avoid app->infra module-level dependency."""
    from app.infrastructure.capabilities.registry import CapabilityRegistry as _CR
    return _CR()
CapabilityRegistry = _CapabilityRegistry  # alias for type annotations

logger = get_logger(__name__)


class TradingWorkflow(BaseWorkflow):
    """End-to-end trading workflow: signal → risk check → order.

    Steps
    -----
    1. ``generate_signal`` — fetch bars, compute indicators, generate signal.
    2. ``risk_check`` — validate against trading policy (limits, hours, breaker).
    3. ``execute_order`` — submit order and emit audit-provenanced event.
    """

    workflow_type = "trading"

    # Default risk parameters — overridden by constructor kwargs.
    _DEFAULT_MAX_POSITION_PCT = 0.10
    _DEFAULT_SINGLE_TRADE_PCT = 0.05
    _DEFAULT_DAILY_LOSS_PCT = 0.02
    _DEFAULT_PORTFOLIO_VALUE = 1_000_000.0

    def __init__(
        self,
        workflow_id: str,
        symbol: str,
        market: MarketCode,
        strategy_name: str = "",
        capability_registry: CapabilityRegistry | None = None,
        trading_policy: TradingPolicy | None = None,
        portfolio_value: float = _DEFAULT_PORTFOLIO_VALUE,
        current_positions: dict[str, float] | None = None,
        sector_allocation: dict[str, float] | None = None,
        user_id: int = 0,
        **kwargs: Any,
    ) -> None:
        self._symbol = symbol
        self._market = market
        self._strategy = strategy_name
        self._portfolio_value = portfolio_value
        self._current_positions = current_positions or {}
        self._sector_allocation = sector_allocation or {}
        self._user_id = user_id

        # Domain services
        self._signal_svc = SignalGenerationService(
            config=SignalConfig(source=SignalSource.TECHNICAL)
        )
        self._policy_svc = TradingPolicyService(policy=trading_policy)
        self._aggregator = SignalAggregator()

        super().__init__(
            workflow_id=workflow_id,
            name=f"Trade {symbol}",
            capability_registry=capability_registry,
            **kwargs,
        )

    def _build_steps(self) -> None:
        self._workflow.add_step("generate_signal", self._step_generate_signal, required=True, timeout=120)
        self._workflow.add_step("risk_check", self._step_risk_check, required=True, timeout=30)
        self._workflow.add_step("execute_order", self._step_execute_order, required=True, timeout=60)

    # ── Step 1: Signal Generation ────────────────────────────────────────

    def _step_generate_signal(self, ctx: Any) -> dict[str, Any]:
        """Fetch bars, compute indicators, and generate a signal."""
        start_ts = time.monotonic()
        logger.info(
            "Step generate_signal: symbol=%s strategy=%s market=%s",
            self._symbol, self._strategy, self._market.value,
        )

        # 1a. Fetch bars via capability registry.
        bars: list[dict[str, Any]] | None = None
        note = "no_bars_fetched"
        try:
            result, fetch_note = self._capabilities.execute(
                "fetch_bars",
                symbol=self._symbol,
                market=self._market.value,
                period="3m",
            )
            bars = result if isinstance(result, list) else None
            note = fetch_note or ("fetched_bars" if bars else "no_bars")
        except Exception as exc:
            logger.warning("Step generate_signal: fetch_bars failed — %s", exc)
            note = f"fetch_error:{exc}"

        bar_count = len(bars) if bars else 0

        # 1b. Compute technical indicators from bars.
        indicators = self._compute_indicators(bars)

        # 1c. Generate signal from technical indicators.
        signal = self._signal_svc.generate_from_technical(
            stock_code=self._symbol,
            indicators=indicators,
        )

        elapsed_ms = round((time.monotonic() - start_ts) * 1000)
        logger.info(
            "Step generate_signal done: signal=%s confidence=%.2f bars=%d ms=%d",
            signal.signal_type, signal.confidence, bar_count, elapsed_ms,
        )

        return {
            "symbol": self._symbol,
            "strategy": self._strategy,
            "signal_type": signal.signal_type,
            "confidence": signal.confidence,
            "strength": signal.strength.value,
            "reason": signal.reason,
            "bar_count": bar_count,
            "note": note,
            "indicators": indicators,
            "elapsed_ms": elapsed_ms,
        }

    # ── Step 2: Risk Check ───────────────────────────────────────────────

    def _step_risk_check(self, ctx: Any) -> dict[str, Any]:
        """Validate the generated signal against trading policy."""
        start_ts = time.monotonic()
        signal_data = ctx.data.get("generate_signal", {})
        signal_type = signal_data.get("signal_type", "hold")
        confidence = signal_data.get("confidence", 0.0)

        logger.info(
            "Step risk_check: symbol=%s signal=%s confidence=%.2f",
            self._symbol, signal_type, confidence,
        )

        # Skip risk check for neutral/hold signals.
        if signal_type == "hold":
            logger.info("Step risk_check: hold signal — skipping policy check")
            return {
                "symbol": self._symbol,
                "risk_action": "skip_hold",
                "violations": [],
                "policy": asdict(self._policy_svc.get_policy()),
                "elapsed_ms": 0,
            }

        # Determine trade direction and estimated value.
        is_buy = signal_type in ("buy", "strong_buy")
        direction = "buy" if is_buy else "sell"

        # Estimate trade value as a fraction of portfolio.
        # Strong signals get larger allocations; weak signals get smaller.
        trade_fraction = min(confidence, 1.0) * self._DEFAULT_SINGLE_TRADE_PCT
        trade_value = self._portfolio_value * trade_fraction

        # 2a. Run policy check.
        if is_buy:
            policy_result: PolicyResult = self._policy_svc.check_buy(
                stock_code=self._symbol,
                trade_value=trade_value,
                portfolio_value=self._portfolio_value,
                current_positions=self._current_positions,
                sector_allocation=self._sector_allocation,
            )
        else:
            policy_result = self._policy_svc.check_sell(
                stock_code=self._symbol,
                trade_value=trade_value,
                portfolio_value=self._portfolio_value,
            )

        elapsed_ms = round((time.monotonic() - start_ts) * 1000)
        logger.info(
            "Step risk_check done: action=%s violations=%d ms=%d",
            policy_result.action.value, len(policy_result.violations), elapsed_ms,
        )

        return {
            "symbol": self._symbol,
            "risk_action": policy_result.action.value,
            "is_allowed": policy_result.is_allowed,
            "is_blocked": policy_result.is_blocked,
            "needs_review": policy_result.needs_review,
            "violations": [v.value for v in policy_result.violations],
            "message": policy_result.message,
            "trade_value": round(trade_value, 2),
            "direction": direction,
            "policy": asdict(self._policy_svc.get_policy()),
            "elapsed_ms": elapsed_ms,
        }

    # ── Step 3: Order Execution ──────────────────────────────────────────

    def _step_execute_order(self, ctx: Any) -> dict[str, Any]:
        """Submit the order and emit an audit-provenanced event."""
        start_ts = time.monotonic()
        risk_data = ctx.data.get("risk_check", {})
        signal_data = ctx.data.get("generate_signal", {})

        risk_action = risk_data.get("risk_action", "")
        signal_type = signal_data.get("signal_type", "hold")

        # Only execute for non-blocked, non-skip signals.
        if risk_action in ("block", "skip_hold"):
            logger.info(
                "Step execute_order: action=%s — skipping execution", risk_action
            )
            return {
                "symbol": self._symbol,
                "order_id": "",
                "status": "skipped",
                "reason": f"risk_action={risk_action}",
                "elapsed_ms": 0,
            }

        # Determine order parameters.
        is_buy = signal_type in ("buy", "strong_buy")
        direction = "buy" if is_buy else "sell"
        trade_value = risk_data.get("trade_value", self._portfolio_value * 0.05)
        price = signal_data.get("indicators", {}).get("close", 0)
        quantity = round(trade_value / price, 2) if price > 0 else 0

        # Generate a provenance ID for audit lineage.
        provenance_id = f"prov_{self._workflow.workflow_id[:12]}"

        # 3a. Attempt real execution via capability registry (if available).
        order_status = "simulated"
        order_id = f"ord_{self._workflow.workflow_id[:8]}"
        exec_note = "simulated"

        try:
            result, note = self._capabilities.execute(
                "execute_order",
                symbol=self._symbol,
                direction=direction,
                quantity=quantity,
                price=price,
                provenance_id=provenance_id,
                market=self._market.value,
            )
            order_status = result.get("status", "executed") if isinstance(result, dict) else "executed"
            order_id = result.get("order_id", order_id) if isinstance(result, dict) else order_id
            exec_note = note or "capability_executed"
        except Exception as exc:
            logger.warning(
                "Step execute_order: capability execute failed — %s (using simulated)", exc
            )
            exec_note = f"fallback_simulated:{exc}"

        # 3b. Emit trade event with mandatory provenance_id for audit lineage.
        try:
            get_event_bus().publish(
                TradeExecutedEvent(
                    source="TradingWorkflow",
                    user_id=self._user_id or 0,
                    symbol=self._symbol,
                    market=self._market.value,
                    action=direction,
                    quantity=quantity,
                    price=price,
                    amount=trade_value,
                    provenance_id=provenance_id,
                )
            )
        except Exception as exc:
            logger.warning("Step execute_order: event emission failed — %s", exc)

        elapsed_ms = round((time.monotonic() - start_ts) * 1000)
        logger.info(
            "Step execute_order done: order_id=%s status=%s provenance=%s ms=%d",
            order_id, order_status, provenance_id, elapsed_ms,
        )

        return {
            "symbol": self._symbol,
            "order_id": order_id,
            "provenance_id": provenance_id,
            "direction": direction,
            "quantity": quantity,
            "price": price,
            "amount": round(trade_value, 2),
            "status": order_status,
            "execution_note": exec_note,
            "elapsed_ms": elapsed_ms,
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _compute_indicators(bars: list[dict[str, Any]] | None) -> dict[str, float]:
        """Derive basic technical indicators from OHLCV bars."""
        if not bars:
            return {}

        closes = [float(b.get("close", 0)) for b in bars if b.get("close")]
        if len(closes) < 2:
            return {"close": closes[0] if closes else 0}

        n = len(closes)
        # Simple moving averages.
        ma5 = sum(closes[-5:]) / min(5, n) if n >= 2 else closes[-1]
        ma20 = sum(closes[-20:]) / min(20, n) if n >= 2 else closes[-1]
        ma60 = sum(closes[-60:]) / min(60, n) if n >= 2 else closes[-1]

        # RSI approximation (simplified 14-period).
        if n >= 15:
            gains = []
            losses = []
            for i in range(-14, 0):
                delta = closes[i] - closes[i - 1]
                gains.append(max(delta, 0))
                losses.append(max(-delta, 0))
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50.0

        return {
            "close": closes[-1],
            "ma5": round(ma5, 4),
            "ma20": round(ma20, 4),
            "ma60": round(ma60, 4),
            "rsi": round(rsi, 2),
            "period_high": round(max(closes), 4),
            "period_low": round(min(closes), 4),
        }
