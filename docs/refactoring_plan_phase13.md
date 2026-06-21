# Domain-Driven Architecture - Phase 13-16 Refactoring Plan

## Current Status

### ✅ Completed (Phase 1-12)

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1-4 | Domain/Application Layer | ✅ |
| Phase 5 | Infrastructure Repos | ✅ |
| Phase 6 | Domain Services | ✅ |
| Phase 7 | Aggregates | ✅ |
| Phase 8 | Event Sourcing | ✅ |
| Phase 9 | Domain Wiring | ✅ |
| Phase 10 | CQRS | ✅ |
| Phase 11 | Tests | ✅ (67 tests) |
| Phase 12 | API | ✅ |

### Deliverables So Far
- Domain Layer: 100+ files
- Application Services: 80+ modules
- CQRS: Commands, Queries, Mediator
- Tests: 67 passing
- APIs: Domain, Events, Health

---

## Phase 13: Service Migration

### Goal
Replace old service implementations with domain-based versions.

### Tasks

#### 13.1 Migrate StockService
- Use `StockScreeningService` for screening
- Use `StockAggregate` for stock operations

#### 13.2 Migrate SignalService
- Use `SignalGenerationService` for signal creation
- Use `SignalAggregator` for composite signals

#### 13.3 Migrate PortfolioService
- Use `PortfolioCalculationService` for metrics
- Use `PortfolioAggregate` for position management

#### 13.4 Replace Direct Calls
- Update `services.py` to use domain facade

### Deliverables
- Migrated service implementations

---

## Phase 14: Performance Optimization

### Goal
Add caching and optimization for domain operations.

### Tasks

#### 14.1 Add Caching
- Cache screening results
- Cache signal calculations

#### 14.2 Add Pagination
- Add pagination to queries

#### 14.3 Add Rate Limiting
- Add rate limiting to commands

### Deliverables
- Cached service layer

---

## Phase 15: Monitoring & Observability

### Goal
Add metrics and monitoring for domain operations.

### Tasks

#### 15.1 Add Metrics
- Track command execution time
- Track query performance

#### 15.2 Add Logging
- Add structured logging

#### 15.3 Add Tracing
- Add request tracing

### Deliverables
- Observable system

---

## Phase 16: Documentation

### Goal
Generate documentation for domain layer.

### Tasks

#### 16.1 Generate API Docs
- OpenAPI specification

#### 16.2 Generate Domain Docs
- Domain model documentation

#### 16.3 Generate Test Coverage
- Coverage reports

### Deliverables
- Documentation

---

## Implementation Order

```
Phase 13 (Service Migration)
├── 13.1 Migrate StockService
├── 13.2 Migrate SignalService
├── 13.3 Migrate PortfolioService
└── 13.4 Replace Direct Calls

Phase 14 (Performance)
├── 14.1 Add Caching
├── 14.2 Add Pagination
└── 14.3 Add Rate Limiting

Phase 15 (Monitoring)
├── 15.1 Add Metrics
├── 15.2 Add Logging
└── 15.3 Add Tracing

Phase 16 (Documentation)
├── 16.1 Generate API Docs
├── 16.2 Generate Domain Docs
└── 16.3 Generate Test Coverage
```

---

## Success Criteria

| Phase | Criteria |
|-------|----------|
| Phase 13 | Services use domain layer |
| Phase 14 | Performance improved |
| Phase 15 | System observable |
| Phase 16 | Documentation complete |

---

## Notes

- Each phase should have verification steps
- Phase 13 is most important - actually uses the new architecture
- Phase 14-16 can be done incrementally