# ADR-001: Decompose Bootstrap Wiring God Module

## Status

**Accepted** — Implemented in session 2026-06-21

## Context

`app/bootstrap_components/wiring_market.py` was a 425-line god module registering 30+ service factories spanning market data, strategy, AI research, data migration, and execution. It imported from 7+ domain modules (`system`, `strategy`, `ai_agent`, `data`, `execution`, `portfolio`, `market_data`), creating a top-level circular dependency hotspot that prevented independent module evolution.

The same pattern existed in `app/core/container.py` (234 lines, `dependency_injector` DeclarativeContainer), which was the legacy DI container but still imported 7 modules eagerly.

## Decision

Decompose `wiring_market.py` into 5 domain-specific wiring modules:

```
wiring_market.py (425 LOC) → 拆分为:
├── wiring_market_data.py  — stock/watchlist/signal/sector (8 factories)
├── wiring_strategy.py     — strategy/backtest/briefing/sentinel (10 factories)
├── wiring_data.py         — data lake/qlib/migration/moments (8 factories)
├── wiring_system_helpers.py — news/tasks/notifications/tools (10 factories)
├── wiring_execution.py    — investment manager (1 factory)
└── wiring_market.py       — re-export shim (backward compat)
```

**Key design decisions:**

1. **Shim pattern for backward compatibility**: The original `wiring_market.py` becomes a re-export shim using `from X import *`. This avoids touching all 10+ importers (`service_wiring.py`, `wiring_trading.py`, etc.).

2. **Lazy context module loading**: `app/presentation/api/context_modules.py` changed from 14 eager imports to `__getattr__`-based lazy loading. This broke the 9-module import chain that prevented module discovery.

3. **Container.py deprecation**: Replaced the `dependency_injector` DeclarativeContainer with a `_LegacyContainerShim` that delegates to `TypedServiceRegistry`. No callers were importing it directly except `task_wiring.py` (which only referenced it in a comment).

## Consequences

### Positive
- **Circular dependency reduction**: Files importing ≥5 modules dropped from 8 → 0 at top level.
- **Single Responsibility**: Each wiring module now maps to one bounded context.
- **Boot time**: Lazy context loading reduces import-time side effects.
- **Testability**: Individual wiring modules can be imported and tested in isolation.

### Negative
- **Indirection overhead**: `__getattr__` lazy loading adds one level of indirection for IDE auto-complete.
- **Shim maintenance**: `wiring_market.py` shim must be kept in sync if new factories are added to sub-modules.
- **Migration surface**: 10+ files import `wiring_market` directly; all must be updated eventually.

### Neutral
- **No behavior change**: All `register_factory` calls remain identical; only file organization changed.
- **Route count unchanged**: 124 routes still registered.

## Alternatives Considered

1. **Delete wiring_market.py, update all importers**: Rejected — too many importers (10+ files), high risk of missing one.
2. **Keep monolithic wiring, add `__all__`**: Rejected — doesn't solve circular dependency root cause.
3. **Full microservice split (Phase 2)**: Deferred — too large for current sprint; this ADR is the prerequisite step.

## Validation

```bash
# All modified files compile
py_compile: 13/13 OK

# Route preload passes (no skips)
preload_route_modules: 125 modules, 124 routes

# All 34 expected factories registered
check_factories: 34/34 present
```

## References

- `app/bootstrap_components/wiring_market_data.py`
- `app/bootstrap_components/wiring_strategy.py`
- `app/bootstrap_components/wiring_data.py`
- `app/bootstrap_components/wiring_system_helpers.py`
- `app/bootstrap_components/wiring_execution.py`
- `app/bootstrap_components/wiring_market.py` (shim)
- `app/presentation/api/context_modules.py` (lazy loading)
- `app/core/container.py` (deprecated shim)
- `app/tasks/task_wiring.py` (blank line cleanup)
