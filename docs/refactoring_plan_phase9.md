# Domain-Driven Architecture - Phase 9-12 Refactoring Plan

## Current Status

### ✅ Completed (Phase 1-8)

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1 | Domain Layer Base | ✅ |
| Phase 2 | Application Interfaces | ✅ |
| Phase 3 | Service Modules | ✅ |
| Phase 4 | DI System | ✅ |
| Phase 5 | Infrastructure Repos | ✅ |
| Phase 6 | Domain Services | ✅ |
| Phase 7 | Aggregates | ✅ |
| Phase 8 | Event Sourcing | ✅ |

### Gaps to Address

| Area | Status | Notes |
|------|--------|-------|
| Domain → App wiring | Partial | Domain services not used by app services |
| CQRS Pattern | None | No command/query separation |
| Integration Tests | None | Missing |
| API Layer | Basic | Could use improvement |

---

## Phase 9: Domain-Application Wiring

### Goal
Connect domain layer to application services.

### Tasks

#### 9.1 Use Domain Services in App Services
- Refactor `StockService` to use `StockScreeningService`
- Refactor `SignalService` to use `SignalGenerationService`
- Refactor `PortfolioService` to use `PortfolioCalculationService`

#### 9.2 Integrate Aggregates
- Add `StockAggregate` usage to relevant endpoints
- Add `PortfolioAggregate` to portfolio management

#### 9.3 Event Publishing
- Connect domain events to application layer
- Emit events on state changes

### Deliverables
- Updated service implementations
- Event wiring

---

## Phase 10: CQRS Implementation

### Goal
Separate commands from queries for better performance.

### Tasks

#### 10.1 Command Handlers
```
app/application/commands/
```
- `CreateStockCommand`
- `UpdatePositionCommand`
- `SubmitOrderCommand`

#### 10.2 Query Handlers
```
app/application/queries/
```
- `GetStockQuery`
- `GetPortfolioQuery`
- `GetOrdersQuery`

#### 10.3 Mediator
```
app/application/mediator.py
```
- Command/query dispatcher

### Deliverables
- CQRS infrastructure

---

## Phase 11: Integration Tests

### Goal
Verify domain layer functionality.

### Tasks

#### 11.1 Domain Service Tests
- Test `StockScreeningService`
- Test `SignalGenerationService`
- Test `PortfolioCalculationService`
- Test `TradingPolicyService`

#### 11.2 Aggregate Tests
- Test `StockAggregate` invariants
- Test `PortfolioAggregate` rebalancing
- Test `TradingSessionAggregate` state machine

#### 11.3 Event Tests
- Test `EventBus` publishing
- Test `EventStore` persistence

### Deliverables
- Test files for domain layer

---

## Phase 12: API Enhancements

### Goal
Improve API layer with domain concepts.

### Tasks

#### 12.1 Domain-First Endpoints
- `/api/domain/stocks` - Domain stock operations
- `/api/domain/portfolio` - Portfolio management
- `/api/domain/orders` - Order management

#### 12.2 Event Endpoints
- `/api/events` - Event history
- `/api/events/replay` - Event replay

#### 12.3 Health Checks
- Domain layer health
- Event store health

### Deliverables
- Enhanced API endpoints

---

## Implementation Order

```
Phase 9 (Domain Wiring)
├── 9.1 Use Domain Services in App Services
├── 9.2 Integrate Aggregates
└── 9.3 Event Publishing

Phase 10 (CQRS)
├── 10.1 Command Handlers
├── 10.2 Query Handlers
└── 10.3 Mediator

Phase 11 (Tests)
├── 11.1 Domain Service Tests
├── 11.2 Aggregate Tests
└── 11.3 Event Tests

Phase 12 (API)
├── 12.1 Domain-First Endpoints
├── 12.2 Event Endpoints
└── 12.3 Health Checks
```

---

## Success Criteria

| Phase | Criteria |
|-------|----------|
| Phase 9 | Domain services used by app services |
| Phase 10 | CQRS pattern implemented |
| Phase 11 | Domain logic tested |
| Phase 12 | API enhanced |

---

## Notes

- Phase 9 is most impactful - connects domain to app
- Phase 11 depends on Phase 9-10
- Phase 12 optional - can be done anytime after Phase 9