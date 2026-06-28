"""Alpha factor module."""

from .alpha_parser import (
    format_validation_error,
    parse_alpha_expression,
    validate_alpha_expression,
)
from .distillation_pipeline import (
    DistillationPipeline,
    PipelineConfig,
    PipelineResult,
    PipelineScheduler,
    PipelineStage,
    PipelineStatus,
    format_pipeline_prompt,
    get_pipeline_scheduler,
)
from .dynamic_search import (
    DecayReason,
    FactorDecayAnalyzer,
    GeneticAlphaSearch,
    SearchStrategy,
    get_decay_analyzer,
    get_search_strategy,
)
from .dynamic_strategy_synthesis import (
    DynamicStrategySynthesizer,
    HotSwapManager,
    MarketRegimeDetector,
    QuickRetrainer,
    RegimeStrategy,
    StrategyType,
    get_strategy_synthesizer,
)
from .factor_manager import (
    FactorDashboard,
    FactorDecayDetector,
    FactorLifecycleManager,
    FactorMetrics,
    get_factor_manager,
)
from .factor_vault import (
    FactorVaultStorage,
    InMemoryFactorVaultStorage,
    MarketRegime,
    get_factor_vault,
)
from .high_fidelity_executor import (
    HighFidelityExecutor,
    LiquidityConstraint,
    TransactionCostConfig,
    format_high_fidelity_prompt,
)
from .high_fidelity_research import (
    CostSource,
    ExecutionCost,
    FidelityAnalysis,
    HighFidelityResearchLoop,
    ProductionResearchBridge,
    format_zero_gap_research_prompt,
    get_production_research_bridge,
)
from .incremental_learning import (
    IncrementalTrainer,
    ModelCheckpoint,
    OnlineLearningScheduler,
    format_incremental_learning_prompt,
    get_incremental_trainer,
    get_online_learning_scheduler,
)
from .meta_learner import (
    MarketCapTier,
    ModelType,
    format_model_selection_prompt,
    get_warm_start_config,
    select_model,
)
from .model_zoo import (
    EnsembleModel,
    ModelConfig,
    ModelZoo,
    format_model_zoo_prompt,
    get_model_zoo,
)
from .numba_operators import (
    NUMBA_OPERATORS,
    apply_operator,
    format_numba_operators_prompt,
    get_operator,
)
from .paper_trading import (
    PaperPosition,
    PaperTrade,
    PaperTradingScheduler,
    PaperTradingStatus,
    get_paper_trading_scheduler,
)
from .portfolio_correlation import (
    CorrelationMatrix,
    PortfolioOptimizer,
    format_correlation_report,
    get_correlation_analyzer,
)
from .postmortem_analysis import (
    FailureType,
    PostMortemAnalysis,
    get_postmortem_analyzer,
)
from .realtime_monitor import (
    AlertManager,
    DataPacket,
    FactorRealtimeMonitor,
    RealTimePusher,
    create_default_alerts,
    get_alert_manager,
    get_factor_monitor,
)
from .weekly_meeting import (
    FactorLifecycleWatcher,
    get_weekly_meeting,
)
from .weekly_meeting_scheduler import (
    WeeklyMeetingConfig,
    get_weekly_meeting_executor,
)
from .worldquant_alphas import (
    ALPHA_EXAMPLES,
    ALPHA_OPERATORS,
    ALPHA_TEMPLATES,
    WorldQuantKnowledge,
    format_alpha_prompt,
    get_complementary_objective_prompt,
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
