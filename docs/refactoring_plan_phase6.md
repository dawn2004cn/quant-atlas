# Domain-Driven Architecture - Phase 6-8 Refactoring Plan

## Current Status

### ✅ Completed (Phase 1-5)

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1 | Domain Layer Base | ✅ |
| Phase 2 | Application Interfaces | ✅ |
| Phase 3 | Service Modules | ✅ |
| Phase 4 | DI System | ✅ |
| Phase 5 | Infrastructure Repos | ✅ |

### Phase 5 Deliverables
- `stock_repository.py` - MySQLStockRepository, MySQLMarketDataRepository
- `signal_repository.py` - MySQLSignalRepository  
- `registry.py` - RepositoryRegistry

---

## Phase 6: Domain Services Layer

### Goal
Move business logic from Application Services into pure Domain Services.

### Existing
- `domain/services/market_analysis_service.py` - MarketAnalysisDomainService (1 service)

### Tasks

#### 6.1 Stock Screening Service
```
app/domain/services/stock_screening_service.py
```
- Rule-based screening engine
- Criteria: price, volume, pe, industry
- Factory for screening rules

#### 6.2 Signal Generation Service
```
app/domain/services/signal_generation_service.py
```
- Signal creation from indicators
- Signal aggregation
- Quality scoring

#### 6.3 Portfolio Calculation Service
```
app/domain/services/portfolio_calculation_service.py
```
- Position valuation
- P&L calculation
- Risk metrics

#### 6.4 Trading Policy Service
```
app/domain/services/trading_policy_service.py
```
- Position limits enforcement
- Circuit breaker logic
- Trading rules

---

## Phase 7: Aggregate Roots

### Goal
Define aggregate roots for complex domain entities with invariants.

### Tasks

#### 7.1 Stock Aggregate
```
app/domain/aggregates/stock_aggregate.py
```
- Stock + MarketData + Signals
- Invariants: valid stock code

#### 7.2 Portfolio Aggregate
```
app/domain/aggregates/portfolio_aggregate.py
```
- Portfolio + Positions
- Invariants: positions <= 100%

#### 7.3 Trading Session Aggregate
```
app/domain/aggregates/trading_session_aggregate.py
```
- Session + Orders + Executions
- Invariants: orders valid before execution

---

## Phase 8: Event Sourcing

### Goal
Add domain event publishing for state changes.

### Tasks

#### 8.1 Event Handlers
```
app/domain/events/handlers.py
```
- Event handler interfaces
- In-memory event bus

#### 8.2 Event Store
```
app/infrastructure/events/event_store.py
```
- Persist domain events
- Event replay capability

#### 8.3 Integration Events
```
app/infrastructure/events/integration_events.py
```
- Emit to external systems
- Celery task dispatch

---

## Implementation Order

```
Phase 6 (Domain Services)
├── 6.1 Stock Screening Service
├── 6.2 Signal Generation Service  
├── 6.3 Portfolio Calculation Service
└── 6.4 Trading Policy Service

Phase 7 (Aggregates)
├── 7.1 Stock Aggregate
├── 7.2 Portfolio Aggregate
└── 7.3 Trading Session Aggregate

Phase 8 (Events)
├── 8.1 Event Handlers
├── 8.2 Event Store
└── 8.3 Integration Events
```

---

## File Structure (Target)

```
app/
├── domain/
│   ├── base.py                    # ✅
│   ├── repositories/           # ✅
│   ├── services/              # NEW
│   │   ├── __init__.py
│   │   ├── stock_screening_service.py
│   │   ├── signal_generation_service.py
│   │   ├── portfolio_calculation_service.py
│   │   └── trading_policy_service.py
│   ├── aggregates/           # NEW
│   │   ├── __init__.py
│   │   ├── stock_aggregate.py
│   │   ├── portfolio_aggregate.py
│   │   └── trading_session_aggregate.py
│   └── events/
│       ├── handlers.py       # NEW
│       └── __init__.py
│
└── infrastructure/
    └── events/
        ├── event_store.py      # NEW
        └── integration_events.py # NEW
```

---

## Success Criteria

| Phase | Criteria |
|-------|----------|
| Phase 6 | 4 domain services with pure business logic |
| Phase 7 | Aggregates enforce invariants |
| Phase 8 | Events publishable/replayable |