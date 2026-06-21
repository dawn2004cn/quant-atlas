# Quant Atlas Architecture Refactoring TODO

**Date**: 2026-04-27
**Principle**: SOLID (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)

---

## 2026-04-27: Midify Plan 9 Implementation Complete

Based on midify_plan9.md, the following agent optimization improvements have been implemented:

### 1. Shared Evidence Blackboard
- Created `app/agents/evidence_blackboard.py`
- Implemented EvidencePoint with structured key-value storage
- Thread-safe EvidenceBlackboard for concurrent agent access
- Agents write structured evidence instead of Markdown reports

### 2. Hierarchical Teams
- Created `app/agents/hierarchical_teams.py`
- Implemented TeamSupervisor for department coordination
- Created department sub-graphs: Fundamental, Quantitative, Risk, Sentiment
- Parallel execution across departments instead of sequential

### 3. Unified Agent Contract
- Created `app/agents/base.py`
- Implemented BaseAgent abstract class
- Implemented AgentResponseDTO with standardized fields
- Conclusion, confidence, evidence_keys, narrative
- Factory functions eliminate dict.get() calls

### 4. RAG-Driven Long-term Memory
- Created `app/agents/agent_memory.py`
- Implemented AgentMemory for tracking decisions/outcomes
- Self-correction through historical failure tracking
- AgentMemoryInjector for context enrichment

### 5. Parallelism & Resilience
- Created `app/agents/parallel_executor.py`
- ParallelAgentExecutor with asyncio.gather
- AgentCircuitBreaker for agent-level isolation
- ResilientAgentWrapper for graceful degradation

---

## 2026-04-27: Midify Plan 8 Implementation Complete

Based on midify_plan8.md, the following advanced optimizations have been implemented:

### 1. DI Container Lifecycle Management
- Enhanced `app/bootstrap_components/container.py`
- Added ServiceScope (SINGLETON, SCOPED, TRANSIENT)
- Implemented RequestScope context manager for web request lifecycle
- Added @inject decorator for declarative dependency injection
- Added cleanup() method for scoped service disposal

### 2. Event-Driven Deep Integration
- Enhanced `app/domain/events.py` with async processing
- Created `app/tasks/event_tasks.py` for Celery async handlers
- Added BusinessEventPublisher with common business scenarios:
  - publish_signal_triggered, publish_order_placed, publish_order_filled
  - publish_risk_violation, publish_backtest_completed
- Implemented AsyncEventProcessor with Celery integration

### 3. External API Circuit Breaker
- Created `app/infrastructure/http/resilient_client.py`
- Implemented ResilientHttpClient with retry, timeout, circuit breaker
- Added Fallback strategies: DefaultFallback, CacheFallback, EmptyListFallback
- Created factory functions: create_akshare_client(), create_ollama_client(), create_fingpt_client()

### 4. Performance Optimization: Vectorized DTO
- Created `app/application/dto/vectorized_dto.py`
- Implemented StockQuotesBatchDTO with numpy arrays for efficient storage
- Implemented MarketDataBatchDTO for OHLCV data
- Added batch filtering and ranking methods
- Created `app/infrastructure/cache/cache_warmer.py` for cache preheating

### 5. AI Agent Explainability
- Enhanced `app/application/services/investment_committee_service.py`
- Added DecisionTree class with node structure and path tracking
- Added decision_tree to CommitteeDecision for visualization
- Created `app/infrastructure/repositories/outcome_repository.py`
- Implemented OutcomeRepository for tracking AI decisions vs actual outcomes
- Added get_adjusted_weights() for dynamic agent weight adjustment

### 6. Code Cleanliness
- Enhanced `app/domain/exceptions.py` with standardized hierarchy
- Added AppError -> DomainError/RepositoryError/ServiceError hierarchy
- Enhanced `app/application/mappers/__init__.py`:
  - Added to_dict_safe() and to_list_safe() utilities
  - Eliminated hasattr checks with type-safe conversion
  - Added BaseModel import handling

---

## 2026-04-27: Midify Plan 7 Implementation Complete

Based on midify_plan7.md, the following optimizations have been implemented:

### 1. Architecture: Modular Contexts (ISP)
- Created `app/bootstrap_components/contexts.py`
- Implemented fine-grained contexts: MarketContext, StrategyContext, AgentContext, TradingContext, DataPipelineContext, TaskContext
- Follows Interface Segregation Principle - avoids "God Object" anti-pattern

### 2. Domain Model: DTO Mapper Layer
- Created `app/application/mappers/__init__.py`
- Implemented BaseMapper abstract class with Entity -> Domain -> DTO conversion
- Added `ensure_dto()` utility to eliminate dict reflection checks

### 3. Data Layer: Multi-level Fallback Strategy
- Created `app/infrastructure/providers/market_data_fallback.py`
- Implemented Strategy Pattern: RealtimeProvider -> CacheProvider -> IndicatorReconstructor
- Added RedisCacheFacade for L1 cache layer

### 4. AI/Agent: Multi-Agent Consensus
- Enhanced `app/application/services/investment_committee_service.py`
- Implemented true multi-agent consensus: TechnicalAgent, FundamentalAgent, SentimentAgent, CriticAgent
- Created `app/infrastructure/repositories/ai_result_repository.py` for result caching

### 5. Task/Event: DomainEvent & Pipeline
- Created `app/domain/events.py` - Observer Pattern implementation
- Created `app/domain/task_pipeline.py` - Pipeline workflow for "data sync -> factor calc -> signal scan"

### 6. Robustness: Risk Control & Circuit Breaker
- Created `app/core/resilience.py`
- Implemented `@require_risk_check` decorator for declarative risk control
- Implemented CircuitBreaker with CLOSED -> OPEN -> HALF_OPEN state transitions

### 7. Performance: Vectorized Compute
- Created `app/infrastructure/compute/vectorized_compute.py`
- Implemented numpy vectorized operations for returns, volatility, Bollinger Bands
- Batch processing for 5000+ securities scanning with DTO list output

### 8. AI-Hedge-Fund Integration
- Created `app/integration/ai_hedge_fund/` module
- Implemented `AIHedgeFundIntegrationService` as platform's "Intelligent Research Team"
- Flow: AI-Hedge-Fund Agents -> Signal Aggregation -> RD-Agent Validation -> Qlib Backtest -> UI Display
- Created adapters: `HedgeFundAgentAdapter`, `RDAgentValidationAdapter`, `QlibValidationAdapter`
- Added API endpoints: `/api/v1/ai-hedge-fund/analyze`, `/api/v1/ai-hedge-fund/agents`
- Created UI page: `ai_hedge_fund.html` with 16+ agent cards, architecture diagram, interactive analysis panel

---

**Previous Updates**:
- **Date**: 2026-04-25
- **Principle**: SOLID

---

## HIGH PRIORITY

### TODO-001: Fix Infrastructure → Application Layer Violations
**Issue**: Infrastructure layer imports application services (reverse dependency)
**Files**:
- `app/infrastructure/qlib/data_adapter.py` (line 10)
- `app/infrastructure/rdagent/submission_validate.py` (lines 8, 39)
- `app/infrastructure/rdagent/qlib_gate.py` (line 9)

**Current**:
```python
# infrastructure/qlib/data_adapter.py
from ...application.services.tool_facade_service import ToolFacadeService  # VIOLATION!
```

**Refactor Approach**:
- Extract shared logic to domain ports
- Use domain events for communication

**Status**: ⏳ Pending

---

### TODO-002: Fix Application → Infrastructure Layer Violations  
**Issue**: Application services import infrastructure directly (inline imports)
**Files**:
- `app/application/services/market_service.py` (line 12)
- `app/application/services/stock_service.py` (line 9)
- `app/application/services/basic_market_data_service.py` (lines 20-27)

**Current**:
```python
# market_service.py
from ...infrastructure.providers.cn_em_industry_map import get_cn_industry_map_cached  # VIOLATION!
```

**Refactor Approach**:
- Inject all infrastructure through constructor
- Create ports for missing interfaces

**Status**: ⏳ Pending

---

### TODO-003: Split Fat Ports Interface File
**Issue**: `domain/ports.py` is 556 lines with 20+ interfaces
**Refactor Approach**:
```
domain/ports/
├── __init__.py
├── market_ports.py      # MarketDataProvider, QuoteProvider, HistoryProvider
├── repository_ports.py  # Repository interfaces
├── agent_ports.py       # AI agent interfaces
├── trading_ports.py     # Trading/Broker interfaces
└── messaging_ports.py   # Task messaging interfaces
```

**Status**: ⏳ Pending

---

### TODO-004: Complete Dependency Injection in Application Services
**Issue**: Services use inline imports despite constructor injection existing

**Current**:
```python
class MarketApplicationService:
    def __init__(self, provider: MarketDataProvider):
        self._provider = provider
    
    def list_quotes(self, market: MarketCode):
        # Uses inline import instead of injected dependency:
        ind_map = get_cn_industry_map_cached(...)  # VIOLATION!
```

**Refactor Approach**:
- Pass all dependencies through constructor
- Remove all inline infrastructure imports

**Status**: ✅ Done (partial - MarketApplicationService uses IndustryProvider)

---

## MEDIUM PRIORITY

### TODO-005: Split Fat MarketDataProvider Interface
**Issue**: Single interface with 6 data methods (violates ISP)

**Current**:
```python
class MarketDataProvider(ABC):
    def get_market_overview(self, market: MarketCode) -> dict: ...
    def get_market_rankings(self, market: MarketCode) -> dict: ...
    def get_realtime_quotes(self, symbols: list[str]) -> list[StockQuote]: ...
    def get_stock_profile(self, symbol: str, market: MarketCode) -> dict: ...
    def get_stock_history(self, symbol: str, market: MarketCode, start: str, end: str) -> list: ...
    def get_chip_distribution(self, symbol: str, market: MarketCode) -> ChipDistribution: ...
```

**Refactor Approach**:
```python
class MarketOverviewPort(ABC):
    def get_market_overview(self, market: MarketCode) -> dict: ...
    def get_market_rankings(self, market: MarketCode) -> dict: ...

class QuotePort(ABC):
    def get_realtime_quotes(self, symbols: list[str]) -> list[StockQuote]: ...
    def get_stock_profile(self, symbol: str, market: MarketCode) -> dict: ...

class HistoryPort(ABC):
    def get_stock_history(self, symbol: str, market: MarketCode, start: str, end: str) -> list: ...

class ChipDataPort(ABC):
    def get_chip_distribution(self, symbol: str, market: MarketCode) -> ChipDistribution: ...

class MarketDataProvider(MarketOverviewPort, QuotePort, HistoryPort, ChipDataPort):
    pass
```

**Status**: ✅ Done

---

### TODO-006: Resolve Application Service Circular Imports
**Issue**: Services importing other application services directly

**Files**:
- `app/application/services/ai_analysis_service.py` → `fingpt_application_service.py`
- `app/application/services/ai_research_service.py` → `fingpt_application_service.py`
- `app/application/services/integration_stack_service.py` → `fingpt_application_service.py`

**Refactor Approach**:
- Extract shared logic to domain layer
- Use service composition in service bundle

**Status**: ✅ Done (already solved via constructor injection)

---

### TODO-007: Fix Presentation → Infrastructure Layer Violations
**Issue**: API routes directly import infrastructure

**Files**:
- `app/presentation/api/routes.py` (lines 13-14, 345, 373, 390)

**Current**:
```python
# routes.py
from ...infrastructure.messaging.task_message_store import TaskMessageStore  # LEAKAGE!
```

**Refactor Approach**:
- Pass infrastructure through ApiV1Context
- Use service bundle from bootstrap

**Status**: ✅ Done

---

## LOW PRIORITY

### TODO-008: Add Market Configuration Mapping
**Issue**: Hardcoded market branches in multiple files

**Current**:
```python
benchmark = ("000300" if market == MarketCode.CN else 
             "SPY" if market == MarketCode.US else 
             "0700.HK" if market == MarketCode.HK else 
             "BTCUSDT")
```

**Refactor Approach**:
- Create `domain/enums/market_config.py`
- Use configuration mapping

**Status**: ✅ Done

---

## COMPLETED (2026-04-25)

| TODO | Description | Status |
|------|-------------|--------|
| - | ToolFacadeService 统一工具门面 | ✅ Done |
| - | Domain ports 扩展 | ✅ Done |
| - | Core utils 扩展 | ✅ Done |
| - | Type annotation 修复 | ✅ Done |
| - | services/ 废弃标记 | ✅ Done |
| - | DTO 规范化 (27个模型) | ✅ Done |
| - | API 版本化策略 (v2) | ✅ Done |
| - | 统一异常处理 | ✅ Done |
| - | 架构稳定性验证 (24 tests) | ✅ Done |

---

## Architecture Principles Reference

### Layer Dependencies (must follow)
```
presentation → application → domain ← infrastructure
```

### SOLID Checklist
- [ ] **S**ingle Responsibility: Each class has one reason to change
- [ ] **O**pen/Closed: Open for extension, closed for modification
- [ ] **L**iskov Substitution: Subtypes are substitutable for base types
- [ ] **I**nterface Segregation: Many focused interfaces > one fat interface
- [ ] **D**ependency Inversion: Depend on abstractions, not concretions