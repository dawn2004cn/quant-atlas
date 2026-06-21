from __future__ import annotations
"""DTO Factory for creating validated DTO instances."""


from typing import Any, Type, Optional
from pydantic import BaseModel, ValidationError

from app.core.logger import get_logger

logger = get_logger(__name__)


class DTOFactory:
    """Factory for creating validated DTO instances."""

    _registry: dict[str, Type[BaseModel]] = {}

    @classmethod
    def register(cls, name: str, dto_class: Type[BaseModel]):
        """Register a DTO class."""
        cls._registry[name] = dto_class
        logger.debug(f"Registered DTO: {name}")

    @classmethod
    def create(cls, name: str, data: dict[str, Any]) -> Optional[BaseModel]:
        """Create a DTO instance from raw data."""
        if name not in cls._registry:
            logger.warning(f"DTO not registered: {name}")
            return None

        dto_class = cls._registry[name]

        try:
            return dto_class(**data)
        except ValidationError as e:
            logger.error(f"DTO validation error for {name}: {e}")
            return None

    @classmethod
    def create_many(cls, name: str, data_list: list[dict[str, Any]]) -> list[BaseModel]:
        """Create multiple DTO instances."""
        return [cls.create(name, data) for data in data_list if cls.create(name, data)]

    @classmethod
    def validate(cls, name: str, data: dict[str, Any]) -> tuple[bool, Optional[BaseModel], list[str]]:
        """Validate data and return result."""
        if name not in cls._registry:
            return False, None, [f"DTO not registered: {name}"]

        dto_class = cls._registry[name]

        try:
            dto = dto_class(**data)
            return True, dto, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, None, errors


def register_dtos():
    """Register all DTOs."""
    from app.application.dto.contracts import (
        BarContract, QuoteContract, StrategySignalContract,
        PositionContract, PortfolioContract, RiskAssessmentContract,
        OrderContract, TechnicalIndicatorContract, AnalysisResultContract,
        TaskContract, EventContract,
    )
    from app.domain.dto.market_data import (
        BarData, QuoteData, StockProfile, MarketStats,
        SignalData, PositionData, RiskAssessmentData,
    )

    DTOFactory.register("bar", BarContract)
    DTOFactory.register("quote", QuoteContract)
    DTOFactory.register("strategy_signal", StrategySignalContract)
    DTOFactory.register("position", PositionContract)
    DTOFactory.register("portfolio", PortfolioContract)
    DTOFactory.register("risk_assessment", RiskAssessmentContract)
    DTOFactory.register("order", OrderContract)
    DTOFactory.register("task", TaskContract)
    DTOFactory.register("event", EventContract)

    DTOFactory.register("bar_data", BarData)
    DTOFactory.register("quote_data", QuoteData)
    DTOFactory.register("stock_profile", StockProfile)
    DTOFactory.register("market_stats", MarketStats)
    DTOFactory.register("signal_data", SignalData)
    DTOFactory.register("position_data", PositionData)
    DTOFactory.register("risk_data", RiskAssessmentData)


def create_dto(dto_name: str, data: dict[str, Any]) -> Optional[BaseModel]:
    """Create a DTO instance (convenience function)."""
    return DTOFactory.create(dto_name, data)


def validate_dto(dto_name: str, data: dict[str, Any]) -> tuple[bool, Optional[BaseModel], list[str]]:
    """Validate a DTO (convenience function)."""
    return DTOFactory.validate(dto_name, data)


__all__ = ["DTOFactory", "register_dtos", "create_dto", "validate_dto"]