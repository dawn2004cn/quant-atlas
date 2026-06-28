"""Alpha factor module."""

from .factor_manager import (
    FactorMetrics,
    FactorDashboard,
    FactorDecayDetector,
    FactorLifecycleManager,
    get_factor_manager,
)

from .worldquant_alphas import (
    WorldQuantKnowledge,
    ALPHA_EXAMPLES,
    ALPHA_OPERATORS,
    ALPHA_TEMPLATES,
    format_alpha_prompt,
    get_complementary_objective_prompt,
)

from .factor_vault import (
    MarketRegime,
    FactorVaultStorage,
    InMemoryFactorVaultStorage,
    get_factor_vault,
)

from .postmortem_analysis import (
    FailureType,
    PostMortemAnalysis,
    get_postmortem_analyzer,
)

from .meta_learner import (
    ModelType,
    MarketCapTier,
    select_model,
    get_warm_start_config,
    format_model_selection_prompt,
)

from .weekly_meeting import (
    FactorLifecycleWatcher,
    get_weekly_meeting,
)

from .high_fidelity_executor import (
    TransactionCostConfig,
    LiquidityConstraint,
    HighFidelityExecutor,
    format_high_fidelity_prompt,
)

from .numba_operators import (
    NUMBA_OPERATORS,
    get_operator,
    apply_operator,
    format_numba_operators_prompt,
)

from .alpha_parser import (
    parse_alpha_expression,
    validate_alpha_expression,
    format_validation_error,
)

from .portfolio_correlation import (
    CorrelationMatrix,
    PortfolioOptimizer,
    get_correlation_analyzer,
    format_correlation_report,
)

from .incremental_learning import (
    ModelCheckpoint,
    IncrementalTrainer,
    OnlineLearningScheduler,
    get_incremental_trainer,
    get_online_learning_scheduler,
    format_incremental_learning_prompt,
)

from .model_zoo import (
    ModelConfig,
    ModelZoo,
    EnsembleModel,
    get_model_zoo,
    format_model_zoo_prompt,
)

from .paper_trading import (
    PaperTradingStatus,
    PaperTrade,
    PaperPosition,
    PaperTradingScheduler,
    get_paper_trading_scheduler,
)

from .weekly_meeting_scheduler import (
    WeeklyMeetingConfig,
    get_weekly_meeting_executor,
)

from .dynamic_search import (
    DecayReason,
    FactorDecayAnalyzer,
    SearchStrategy,
    GeneticAlphaSearch,
    get_decay_analyzer,
    get_search_strategy,
)

from .distillation_pipeline import (
    PipelineStage,
    PipelineStatus,
    PipelineConfig,
    PipelineResult,
    DistillationPipeline,
    PipelineScheduler,
    get_pipeline_scheduler,
    format_pipeline_prompt,
)

from .dynamic_strategy_synthesis import (
    StrategyType,
    RegimeStrategy,
    MarketRegimeDetector,
    DynamicStrategySynthesizer,
    QuickRetrainer,
    HotSwapManager,
    get_strategy_synthesizer,
)

from .high_fidelity_research import (
    CostSource,
    ExecutionCost,
    FidelityAnalysis,
    HighFidelityResearchLoop,
    ProductionResearchBridge,
    get_production_research_bridge,
    format_zero_gap_research_prompt,
)

from .realtime_monitor import (
    DataPacket,
    RealTimePusher,
    FactorRealtimeMonitor,
    AlertManager,
    get_factor_monitor,
    get_alert_manager,
    create_default_alerts,
)

__all__ = [
    "FactorMetrics",
    "FactorDashboard",
    "FactorDecayDetector",
    "FactorLifecycleManager",
    "get_factor_manager",
    "WorldQuantKnowledge",
    "ALPHA_EXAMPLES",
    "ALPHA_OPERATORS",
    "ALPHA_TEMPLATES",
    "format_alpha_prompt",
    "get_complementary_objective_prompt",
]
