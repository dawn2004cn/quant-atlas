# Architectural Analysis & Refactoring Plan

## Current Architecture Issues

### 1. Single Responsibility Principle Violations
- **Application Layer**: 100+ services in flat `services/` directory - too many responsibilities
- **Domain Layer**: Mixed alpha/trading/research/execution in single packages
- **Infrastructure**: Repositories and external integrations intertwined

### 2. Open/Closed Principle Issues
- Hard to extend features without modifying existing code
- No plugin architecture for new strategies/research methods

### 3. Liskov Substitution Issues
- Inconsistent interface implementations across repositories
- No abstract base for similar service types

### 4. Interface Segregation Issues
- Large port interfaces (e.g., `repository_ports.py` with multiple methods)
- Services depend on unnecessary interfaces

### 5. Dependency Inversion Issues
- Direct dependencies on concrete implementations
- No domain-first dependency injection

### 6. Package Structure Issues
```
app/
├── domain/           # Has 20+ subpackages - too flat
│   ├── alpha/       # Should be: domain/research/alpha
│   ├── risk/       # Should be: domain/policy/risk
│   └── ...
├── application/     # 100+ services in flat structure
├── infrastructure/ # Mixed concerns
└── presentation/   # 60+ route files
```

---

## Refactoring Plan

### Phase 1: Package Reorganization (Non-breaking)
- Rename and group domain subpackages
- Create feature-based modules
- Add module `__init__.py` exports

### Phase 2: Interface Consolidation
- Refactor port interfaces to be smaller
- Add adapter pattern for external integrations
- Create domain-driven repository abstractions

### Phase 3: Service Grouping
- Group related services into submodules
- Add service facades for common operations
- Implement CQRS more consistently

### Phase 4: Dependency Injection
- Add DI container
- Refactor services to depend on interfaces
- Enable easier testing

---

## Proposed Target Architecture

```
app/
├── domain/                          # Pure domain logic
│   ├── entities/                    # Domain entities
│   ├── aggregates/                 # Domain aggregates
│   ├── value_objects/              # Value objects
│   ├── services/                   # Domain services
│   ├── ports/                      # Hexagonal ports
│   ├── events/                     # Domain events
│   ├── research/                   # Alpha research (moved from alpha/)
│   ├── policy/                     # Risk/policy (moved from risk/)
│   └── execution/                  # Trading execution
│
├── application/                   # Application services
│   ├── services/                   # Grouped by feature
│   │   ├── trading/               # Trading services
│   │   ├── research/             # Research services
│   │   └── portfolio/            # Portfolio services
│   ├── commands/                   # CQRS commands
│   ├── queries/                    # CQRS queries
│   ├── dto/                        # Data transfer objects
│   └── facades/                    # Service facades
│
├── infrastructure/                  # External integrations
│   ├── persistence/                # Repository implementations
│   ├── external/                   # External API adapters
│   ├── messaging/                  # Message queue
│   ├── qlib/                     # Qlib integration
│   └── tdx/                       # TDX data
│
├── presentation/                   # API layer
│   ├── api/                       # REST endpoints
│   ├── web/                       # Web UI
│   └── handlers/                  # Shared handlers
│
└── bootstrap/                      # DI and bootstrapping
```

---

## SOLID Compliance Checklist

| Principle | Current | Target |
|-----------|---------|--------|
| SRP | ❌ Flat service dir | ✅ Grouped services |
| OCP | ❌ Hard to extend | ✅ Plugin architecture |
| LSP | ⚠️ Inconsistent | ✅ Base abstractions |
| ISP | ❌ Large ports | ✅ Small interfaces |
| DIP | ❌ Direct deps | ✅ DI container |
| SRP-Domain | ❌ Mixed modules | ✅ Bounded contexts |

---

## Implementation Priority

1. **Immediate**: Package reorganization (safe, non-breaking)
2. **Short-term**: Port interface refinement  
3. **Medium-term**: Service grouping
4. **Long-term**: Full DI container

Ready to proceed with Phase 1?