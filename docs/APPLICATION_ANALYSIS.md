# Application Layer Analysis & Refactoring Plan

## Current State

### Services Statistics
- **Total Services**: ~127 application services
- **Location**: `app/application/services/` (flat structure)
- **Domain Services**: 5 in `app/domain/services/`

### SOLID Violations Identified

| Issue | Count | SOLID Principle |
|-------|-------|----------------|
| Mixed responsibilities in services | High | SRP |
| Direct dependencies on infrastructure | High | DIP |
| No service grouping | High | SRP |
| Large service classes | Medium | SRP |
| Duplicate code across services | Medium | DRY |

### Service Categories (Proposed)

```
app/application/services/
├── trading/           # Trading, portfolio, orders
├── market_data/      # Market data, quotes, history  
├── research/         # Alpha, factors, backtest
├── user/            # User, auth, preferences
├── integration/     # External APIs
├── analytics/       # Analysis, reporting
└── ops/            # Operations, monitoring
```

### Current Issues

1. **God Classes**: Some services have 1000+ lines
2. **Mixed Concerns**: E.g. `smart_briefing_service.py` handles both NLP and trading
3. **Direct DB Access**: Services directly use SQLAlchemy instead of repositories
4. **No Interfaces**: Services don't implement port interfaces

### Dependencies Problem

```python
# Current (violates DIP)
from app.infrastructure.repositories.mysql import MySQLStockRepository

# Should be
from app.domain.ports import IStockRepository
from app.infrastructure.repositories import StockRepository  # impl
```

---

## Refactoring Plan

### Phase 1: Service Grouping (Safe)
- Create subdirectories for service categories
- Move existing services to appropriate groups
- Add `__init__.py` with backward-compatible exports

### Phase 2: Extract Interfaces
- Ensure services implement ABC interfaces
- Move interfaces to `app/application/interfaces/`

### Phase 3: Dependency Injection
- Add DI container for services
- Remove direct infrastructure imports

### Phase 4: Split God Classes
- Identify services > 500 lines
- Extract into smaller focused services

---

## Implementation Priority

1. **Immediate**: Create service group directories (safe, non-breaking)
2. **Short-term**: Add interface definitions  
3. **Medium-term**: Introduce DI container
4. **Long-term**: Split large services

Ready to proceed?