# Domain-Driven Architecture - Refactoring Plan (Phase 5-8)

## Current Status

### ✅ Completed (Phase 1-4)
- Domain Layer Base: `Entity`, `AggregateRoot`, `ValueObject`, `IRepository`
- Repository Interfaces: `IStockRepository`, `ISignalRepository`, `IMarketDataRepository`
- Application Services: 80+ service modules
- DI System: ServiceFactory + container

### 📊 Gaps Identified

| Area | Status | Files |
|------|--------|-------|
| Domain Entities | Partial | entities.py, stock.py, signal.py |
| Domain Ports | Partial | ports/*.py |
| Infrastructure Repos | Scattered | infra/repositories/*.py |
| Domain Services | Minimal | domain/services/*.py |
| Aggregates | None | - |
| Event System | None | events_core.py (unused) |

---

## Phase 5: Infrastructure Implementations

### Goal
Implement domain repository interfaces with concrete infrastructure adapters.

### Tasks

#### 5.1 MySQL Stock Repository
```
app/infrastructure/repositories/stock_repository.py
```
- Implement `IStockRepository`
- Map to existing `stock.basic_market_data` table
- Methods: `get_by_code`, `list_by_market`, `search`

#### 5.2 MySQL Signal Repository  
```
app/infrastructure/repositories/signal_repository.py
```
- Implement `ISignalRepository`
- Map to `signal_flag_pool` table
- Methods: `save`, `find_by_stock`, `list_recent`

#### 5.3 Market Data Repository
```
app/infrastructure/repositories/market_data_repository.py
```
- Implement `IMarketDataRepository`
- Use qlib data or TDX data
- Methods: `get_daily`, `get_latest`, `get_range`

#### 5.4 Repository Registry
```
app/infrastructure/repositories/registry.py
```
- Central registry for all repositories
- Factory pattern for repository creation

### Deliverables
- 4 new infrastructure repository files
- All domain interfaces implemented

---

## Phase 6: Domain Services Layer

### Goal
Move business logic from Application Services into Domain Services.

### Tasks

#### 6.1 Stock Screening Service
```
app/domain/services/stock_screening_service.py
```
- Domain logic for stock filtering
- Rule-based screening engine
- Factory for screening criteria

#### 6.2 Signal Generation Service
```
app/domain/services/signal_generation_service.py
```
- Domain logic for signal creation
- Signal aggregation logic
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
- Trading rules enforcement
- Position limits
- Circuit breaker logic

### Deliverables
- 4 new domain service files
- Business logic extracted from app services

---

## Phase 7: Aggregate Roots

### Goal
Define aggregate roots for complex domain entities.

### Tasks

#### 7.1 Stock Aggregate
```
app/domain/aggregates/stock_aggregate.py
```
- Stock + MarketData + Signals
- Invariants: stock must have valid code
- Methods: `add_signal`, `get_latest_price`

#### 7.2 Portfolio Aggregate
```
app/domain/aggregates/portfolio_aggregate.py
```
- Portfolio + Positions + Orders
- Invariants: positions sum to < 100%
- Methods: `add_position`, `rebalance`

#### 7.3 Trading Session Aggregate
```
app/domain/aggregates/trading_session_aggregate.py
```
- Session + Orders + Executions
- Invariants: orders valid before execution
- Methods: `submit_order`, `execute`

### Deliverables
- 3 aggregate root files
- Invariant validation

---

## Phase 8: Event Sourcing

### Goal
Add domain event publishing for state changes.

### Tasks

#### 8.1 Domain Event Handlers
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
- Emit events to external systems
- Celery task dispatch

### Deliverables
- Event system infrastructure
- Event-driven architecture foundation

---

## File Structure (Target)

```
app/
├── domain/
│   ├── base.py                    # ✅ Existing
│   ├── entities.py               # ✅ Existing
│   ├── repositories/
│   │   ├── stock.py             # ✅ Existing
│   │   └── signal.py            # ✅ Existing
│   ├── services/                # (empty)
│   │   └── __init__.py
│   ├── aggregates/              # NEW
│   │   ├── __init__.py
│   │   ├── stock_aggregate.py
│   │   ├── portfolio_aggregate.py
│   │   └── trading_session_aggregate.py
│   ├── events/
│   │   ├── handlers.py         # NEW
│   │   └── __init__.py
│   └── ports/                   # ✅ Existing
│
├── application/
│   ├── interfaces.py            # ✅ Existing
│   ├── factory.py               # ✅ Existing
│   └── services/               # ✅ Existing (80+)
│
└── infrastructure/
    └── repositories/
        ├── stock_repository.py     # NEW
        ├── signal_repository.py    # NEW
        ├── market_data_repository.py # NEW
        └── registry.py             # NEW
    └── events/
        ├── event_store.py          # NEW
        └── integration_events.py   # NEW
```

---

## Implementation Order

```
Phase 5 (Infrastructure Repos)
├── 5.1 MySQL Stock Repository
├── 5.2 MySQL Signal Repository
├── 5.3 Market Data Repository
└── 5.4 Repository Registry

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

## Success Criteria

| Phase | Criteria |
|-------|----------|
| Phase 5 | All domain interfaces have implementations |
| Phase 6 | Business logic moved to domain services |
| Phase 7 | Aggregates enforce invariants |
| Phase 8 | Domain events can be published/replayed |

---

## Notes

- Keep existing application services as orchestration layer
- Domain services handle pure business logic
- Infrastructure repositories use existing DB connections
- Events are optional - add incrementally