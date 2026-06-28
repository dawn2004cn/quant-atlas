"""Domain services - pure business logic without IO."""

from .domain_services import MarketDomainService, RiskDomainService, SignalDomainService
from .market_analysis_service import MarketAnalysisDomainService
from .portfolio_calculation_service import (
    PortfolioCalculationService,
    PortfolioSnapshot,
    PortfolioValuator,
    Position,
    PositionSide,
    PositionSnapshot,
    RiskMetrics,
)
from .rdagent_config import parse_rdagent_loop_params
from .regime_manager import MarketRegimeManager
from .signal_generation_service import (
    GeneratedSignal,
    SignalAggregator,
    SignalConfig,
    SignalGenerationService,
    SignalSource,
    SignalStrength,
)
from .stock_screening_service import (
    PriceRange,
    ScreeningCriteria,
    ScreeningRule,
    ScreeningRuleFactory,
    StockScreeningService,
)
from .trading_policy_service import (
    PolicyResult,
    PolicyViolation,
    TradingAction,
    TradingPolicy,
    TradingPolicyService,
    TradingRuleEngine,
)

__all__ = [
    # Existing
    "RiskDomainService",
    "SignalDomainService",
    "MarketDomainService",
    "MarketAnalysisDomainService",
    "parse_rdagent_loop_params",
    "MarketRegimeManager",
    # Phase 6: Stock Screening
    "ScreeningCriteria",
    "PriceRange",
    "ScreeningRule",
    "StockScreeningService",
    "ScreeningRuleFactory",
    # Phase 6: Signal Generation
    "SignalStrength",
    "SignalSource",
    "SignalConfig",
    "GeneratedSignal",
    "SignalGenerationService",
    "SignalAggregator",
    # Phase 6: Portfolio Calculation
    "PositionSide",
    "Position",
    "PositionSnapshot",
    "PortfolioSnapshot",
    "RiskMetrics",
    "PortfolioCalculationService",
    "PortfolioValuator",
    # Phase 6: Trading Policy
    "PolicyViolation",
    "TradingAction",
    "TradingPolicy",
    "PolicyResult",
    "TradingPolicyService",
    "TradingRuleEngine",
]
