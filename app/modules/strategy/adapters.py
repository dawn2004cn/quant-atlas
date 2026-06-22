"""Strategy Service Adapters.

Adapters implement the Strategy Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.strategy.ports import (
    AttributionPort,
    BriefingPort,
    FactorPort,
    RecommendationPort,
    ReviewPort,
    SignalFlagPort,
    SignalObservationPort,
    StrategyCopilotPort,
    StrategyOptimizationPort,
    StrategySnapshotPort,
    StrategySynthesisPort,
)


class RecommendationAdapter(RecommendationPort):
    """Adapts RecommendationService to RecommendationPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def daily_top(self, market: str, top_n: int, account_equity: float) -> list[dict[str, Any]]:
        return self._service.daily_top(
            market=market,
            top_n=top_n,
            account_equity=account_equity,
        )


class StrategyOptimizationAdapter(StrategyOptimizationPort):
    """Adapts StrategyOptimizationService to StrategyOptimizationPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def run_walk_forward(
        self,
        symbol: str,
        param_space: dict[str, Any],
        start_date: str,
        end_date: str,
        objective: str,
        train_window_days: int,
        test_window_days: int,
        n_windows: int,
    ) -> dict[str, Any]:
        result = self._service.run_walk_forward(
            symbol=symbol,
            param_space=param_space,
            start_date=start_date,
            end_date=end_date,
            objective=objective,
            train_window_days=train_window_days,
            test_window_days=test_window_days,
            n_windows=n_windows,
        )
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if hasattr(result, "dict"):
            return result.dict()
        return result


class StrategySnapshotAdapter(StrategySnapshotPort):
    """Adapts StrategySnapshotService to StrategySnapshotPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_snapshot(self, strategy_id: str) -> dict[str, Any]:
        return self._service.get_snapshot(strategy_id)


class StrategyCopilotAdapter(StrategyCopilotPort):
    """Adapts StrategyCoPilotService to StrategyCopilotPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def analyze_strategy(self, strategy_id: str, query: str) -> dict[str, Any]:
        return self._service.analyze_strategy(strategy_id, query)


class SignalObservationAdapter(SignalObservationPort):
    """Adapts SignalObservationService to SignalObservationPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def record_observation(self, signal_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        return self._service.record_observation(signal_id, outcome)

    def get_observations(self, signal_id: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._service.get_observations(signal_id, limit=limit)


class SignalFlagAdapter(SignalFlagPort):
    """Adapts SignalFlagScannerService to SignalFlagPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def scan_flags(self, symbols: list[str], strategy_id: str) -> dict[str, Any]:
        return self._service.scan_flags(symbols, strategy_id)


class AttributionAdapter(AttributionPort):
    """Adapts UnifiedAttributionService to AttributionPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_attribution(self, strategy_id: str, period: str) -> dict[str, Any]:
        return self._service.get_attribution(strategy_id, period)


class ReviewAdapter(ReviewPort):
    """Adapts review tracking service to ReviewPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def submit_review(self, strategy_id: str, review_data: dict[str, Any]) -> dict[str, Any]:
        return self._service.submit_review(strategy_id, review_data)

    def get_reviews(self, strategy_id: str) -> list[dict[str, Any]]:
        return self._service.get_reviews(strategy_id)


class BriefingAdapter(BriefingPort):
    """Adapts SmartDailyBriefingService to BriefingPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def get_briefing(self, user_id: int) -> dict[str, Any]:
        return self._service.get_briefing(user_id)


class StrategySynthesisAdapter(StrategySynthesisPort):
    """Adapts StrategySynthesizerService to StrategySynthesisPort."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def synthesize(self, market_regime: str, constraints: dict[str, Any]) -> dict[str, Any]:
        return self._service.synthesize(market_regime, constraints)


class FactorAdapter(FactorPort):
    """Adapts factor services to FactorPort."""

    def __init__(self, ortho_service: Any = None, correction_service: Any = None) -> None:
        self._ortho = ortho_service
        self._correction = correction_service

    def list_factors(self, category: str | None = None) -> list[dict[str, Any]]:
        # Placeholder: actual implementation depends on factor service interface
        return []

    def get_factor(self, factor_id: str) -> dict[str, Any]:
        # Placeholder: actual implementation depends on factor service interface
        return {"id": factor_id}


def create_strategy_ports(ctx: Any) -> dict[str, Any]:
    """Create all strategy ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    if getattr(ctx, "recommendation_service", None) is not None:
        ports["recommendation"] = RecommendationAdapter(ctx.recommendation_service)

    if getattr(ctx, "strategy_optimization_service", None) is not None:
        ports["strategy_optimization"] = StrategyOptimizationAdapter(
            ctx.strategy_optimization_service
        )

    if getattr(ctx, "strategy_shadow_service", None) is not None:
        # StrategyShadowService doesn't have a clear port yet
        pass

    if getattr(ctx, "strategy_copilot_service", None) is not None:
        ports["strategy_copilot"] = StrategyCopilotAdapter(ctx.strategy_copilot_service)

    if getattr(ctx, "signal_observation_service", None) is not None:
        ports["signal_observation"] = SignalObservationAdapter(
            ctx.signal_observation_service
        )

    if getattr(ctx, "signal_flag_service", None) is not None:
        ports["signal_flag"] = SignalFlagAdapter(ctx.signal_flag_service)

    if getattr(ctx, "review_tracking_service", None) is not None:
        ports["review"] = ReviewAdapter(ctx.review_tracking_service)

    if getattr(ctx, "smart_daily_briefing_service", None) is not None:
        ports["briefing"] = BriefingAdapter(ctx.smart_daily_briefing_service)

    if getattr(ctx, "strategy_synthesizer_service", None) is not None:
        ports["strategy_synthesis"] = StrategySynthesisAdapter(
            ctx.strategy_synthesizer_service
        )

    if getattr(ctx, "factor_orthogonalization_service", None) is not None or getattr(
        ctx, "factor_self_correction_service", None
    ) is not None:
        ports["factor"] = FactorAdapter(
            getattr(ctx, "factor_orthogonalization_service", None),
            getattr(ctx, "factor_self_correction_service", None),
        )

    return ports


__all__ = [
    "RecommendationPort",
    "StrategyOptimizationPort",
    "StrategySnapshotPort",
    "StrategyCopilotPort",
    "SignalObservationPort",
    "SignalFlagPort",
    "AttributionPort",
    "ReviewPort",
    "BriefingPort",
    "StrategySynthesisPort",
    "FactorPort",
    "RecommendationAdapter",
    "StrategyOptimizationAdapter",
    "StrategySnapshotAdapter",
    "StrategyCopilotAdapter",
    "SignalObservationAdapter",
    "SignalFlagAdapter",
    "AttributionAdapter",
    "ReviewAdapter",
    "BriefingAdapter",
    "StrategySynthesisAdapter",
    "FactorAdapter",
    "create_strategy_ports",
]
