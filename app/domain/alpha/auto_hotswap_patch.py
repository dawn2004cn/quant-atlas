"""Auto Hot-Swap trigger — EvolutionArbiter patch.

This module lives in the domain layer but needs to patch an application-layer
service (``MetaArbiterService``).  To respect DIP, we use a string-based
lazy import so that the domain never directly imports application code.
The patch is activated by the import at the bottom of ``bootstrap.py``'s
``_initialize_side_effects()`` function.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

from app.core.event_bus import EVENT_PRIORITY_HIGH, Event, get_event_bus
from app.core.logger import get_logger

logger = get_logger(__name__)


class SynthesizeMethod(Protocol):
    """Minimal protocol matching MetaArbiterService.synthesize signature."""

    def __call__(self, symbol: str, market: str,
                 verdict_hint: Any | None, use_llm: bool) -> Any:
        ...


@dataclass
class StrategySwapOutEvent(Event):
    symbol: str = ""
    market: str = "CN"
    old_strategy: str = ""
    reason: str = ""
    trigger_score_sharpe: float = 0.0


def auto_trigger_hot_swap(symbol: str, market: str = "CN", min_sharpe: float = 0.8) -> bool:
    tournament: EvolutionTournament = get_tournament()
    top = tournament.get_top_strategies(3)[0] if tournament.get_top_strategies(3) else None
    if top is None:
        logger.warning("No leaderboard for %s (%s); hot-swap skipped", symbol, market)
        return False
    current_sharpe = float(top.sharpe or 0.0)
    if current_sharpe >= min_sharpe:
        return False
    logger.info("Hot-swap candidate: %s performance decay (Sharpe=%.3f)", top.strategy_id, current_sharpe)
    get_event_bus().publish(
        StrategySwapOutEvent(
            timestamp=datetime.now(),
            source="AlphaHotSwap",
            priority=EVENT_PRIORITY_HIGH,
            symbol=symbol,
            market=market,
            old_strategy=top.strategy_id,
            reason="performance_decay",
            trigger_score_sharpe=current_sharpe,
        )
    )
    return True


_original_synthesize: SynthesizeMethod | None = None


def _patched_synthesize(self: Any, symbol: str, market: str = "CN",
                        verdict_hint: Any | None = None, use_llm: bool = False) -> Any:
    result = _original_synthesize(self, symbol, market, verdict_hint, use_llm)  # type: ignore[misc]
    try:
        auto_trigger_hot_swap(symbol, market)
    except Exception as exc:
        logger.warning("Hot-swap trigger failed for %s: %s", symbol, exc)
    return result


def enable_hot_swap_patch() -> None:
    """Activate the auto hot-swap monkey patch on MetaArbiterService.

    Uses string-based import to avoid domain→application dependency at load time.
    Safe to call multiple times (idempotent).
    """
    global _original_synthesize

    if _original_synthesize is not None:
        return  # Already patched

    # Lazy import via string — prevents domain layer from pulling in
    # application-layer code at module load time.
    from app.application.services.orchestration.meta_arbiter_service import MetaArbiterService  # noqa: PLC0414

    _original_synthesize = MetaArbiterService.synthesize  # type: ignore[misc]
    MetaArbiterService.synthesize = _patched_synthesize  # type: ignore[assignment]
    logger.info("EvolutionArbiter patched: auto hot-swap trigger enabled")


# Backward-compat: module-level call on import for existing users.
# New code should call enable_hot_swap_patch() explicitly.
if _original_synthesize is None:
    try:
        enable_hot_swap_patch()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Hot-swap patch initialization failed (non-fatal): %s", exc)
