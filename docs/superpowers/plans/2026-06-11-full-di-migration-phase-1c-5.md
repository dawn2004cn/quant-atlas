# Full DI Migration (Phase 1c–5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the global mutable bind/get proxy pattern, unify wiring to ServiceRegistry, split create_app() into testable steps, and de-duplicate modules/ vs application/.

**Architecture:** Migrate 36 bind/get proxy modules + ~45 wire_* functions to declarative `@register_service` / `register_factory` registrations in `ServiceRegistry`. Each service gets constructor injection. The 37 `_access.py` alias modules are deprecated (kept for backward compat, emit `DeprecationWarning`). The `Services` class loses its `__getattr__` fallback and 100+ `= None` class attributes. `create_app()` is split into 6 importable configuration functions.

**Tech Stack:** Python 3.10+, Flask, `app.core.registry.ServiceRegistry`, existing `@register_service`/`@register_factory` decorators.

---

## SPRINT 0: Baseline & scaffolding

### Task 0.0: Write baseline test for registry state

**Files:**
- Create: `tests/bootstrap/test_registry_baseline.py`

- [ ] **Step 1: Write a baseline test that captures current state**

```python
"""Baseline test: capture current registry state before migration."""
import pytest
from app.core.registry import registered_service_names, registered_route_names, registered_factories_names


def test_baseline_registered_services():
    """Current: ~16 factory-registered services."""
    names = registered_service_names()
    assert "stock_service" in names
    assert "market_service" in names
    assert "basic_market_data_service" in names


def test_baseline_registered_factories():
    """Current: register_factory entries exist for complex services."""
    from app.bootstrap_components.service_wiring import _factories
    assert "stock_service" in _factories
    assert "market_service" in _factories
    assert "ai_analysis_service" in _factories
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/bootstrap/test_registry_baseline.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/bootstrap/test_registry_baseline.py
git commit -m "test: baseline registry state capture"
```

### Task 0.1: Create deprecation audit tool

**Files:**
- Create: `scripts/audit_bind_get_usage.py`

- [ ] **Step 1: Create the audit script**

```python
#!/usr/bin/env python
"""Audit remaining get_*() consumer calls across the codebase."""
from pathlib import Path
import re
import sys

HELPERS_DIR = Path(__file__).parent.parent / "app" / "application" / "services" / "helpers"
APP_DIR = Path(__file__).parent.parent / "app"

def find_consumers():
    """Find all files importing get_* from _wiring or _access modules."""
    consumers = {}
    for py_file in APP_DIR.rglob("*.py"):
        if "helpers" in str(py_file) and py_file.suffix == ".py":
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Match imports from *_wiring or *_access
        matches = re.findall(
            r"from\s+app\.application\.services\.helpers\.(\w+_(?:wiring|access))\s+import\s+((?:get_\w+(?:\s*,\s*)?)+)",
            text,
        )
        if matches:
            consumers[str(py_file.relative_to(APP_DIR))] = matches
        # Also match direct get_* calls from helpers
        for _, mod, gets in matches:
            for get_fn in re.findall(r"get_\w+", gets):
                consumers.setdefault(str(py_file.relative_to(APP_DIR)), []).append((mod, get_fn))
    return consumers

if __name__ == "__main__":
    consumers = find_consumers()
    for path, imports in sorted(consumers.items()):
        print(f"\n{path}")
        for mod, fn in imports:
            print(f"  from {mod} import {fn}")
    print(f"\nTotal consumer files: {len(consumers)}")
    sys.exit(0)
```

- [ ] **Step 2: Run the audit**

Run: `python scripts/audit_bind_get_usage.py > instance/bind_get_audit.txt`
Expected: Output of ~40 consumer files

- [ ] **Step 3: Commit**

```bash
git add scripts/audit_bind_get_usage.py
git commit -m "tool: add bind/get usage audit script"
```

---

## SPRINT 1: Migrate simple wire_* functions to @register_service

These 36 wire_* functions across wiring_market.py, wiring_ai.py, wiring_trading.py, wiring_system.py are the easiest — they use `ServiceInjector` and can become `@register_service` entries.

### Task 1.0: Migrate injector-based wire_* from wiring_market.py

**Files:**
- Modify: `app/bootstrap_components/wiring_market.py`

- [ ] **Step 1: Replace injector-based wires with @register_service**

```python
# Before: wire_strategy_service uses ServiceInjector
def wire_strategy_service(services: Any) -> None:
    global _injector
    if _injector is None or _injector._services is not services:
        _injector = ServiceInjector(services)
    try:
        from app.modules.strategy.services.strategy_service import StrategyService
        _injector.inject(StrategyService)
    except Exception as exc:
        logger.warning("Could not wire strategy_service: %s", exc)

# After: register as a service class (if StrategyService.__init__ uses typed params)
# OR as a factory for complex ones:
register_factory("strategy_service", lambda _: StrategyService())
```

Each wire becomes either:
- `@register_service` if the service constructor takes zero args or only types resolvable by ServiceRegistry
- `register_factory("name", lambda _: ServiceClass())` if it needs no dependencies

- [ ] **Step 2: Delete the _injector global and all injector imports from wiring_market.py**

Remove: `_injector: ServiceInjector | None = None`, the `if _injector is None` guard block from each function.

- [ ] **Step 3: Keep wire_* shims for backward compat (deprecated)**

```python
# Backward compat shim (deprecated)
def wire_strategy_service(services: Any) -> None:
    """DEPRECATED: Use ServiceRegistry instead."""
    import warnings
    warnings.warn(
        "wire_strategy_service is deprecated; use ServiceRegistry",
        DeprecationWarning,
        stacklevel=2,
    )
```

- [ ] **Step 4: Run existing tests to verify no regression**

Run: `pytest tests/bootstrap/ tests/core/ -q`
Expected: PASS (or close to it — some tests may need updates)

### Task 1.1: Migrate wire_* from wiring_ai.py

**Files:**
- Modify: `app/bootstrap_components/wiring_ai.py`

Same pattern as 1.0. `wire_fingpt_application_service` needs special handling (it takes settings/session_factory) — keep as `register_factory` (already done partially).

- [ ] **Step 1: Convert simple wires to register_factory**

- [ ] **Step 2: Keep deprecated wire_* shims**

- [ ] **Step 3: Run tests**

### Task 1.2: Migrate wire_* from wiring_trading.py

**Files:**
- Modify: `app/bootstrap_components/wiring_trading.py`

`wire_trading_risk_services`, `wire_trading_execution` take extra args — keep as `register_factory`. Simple injectors become `register_factory`.

- [ ] **Step 1: Convert wires**

- [ ] **Step 2: Keep deprecated shims**

- [ ] **Step 3: Run tests**

### Task 1.3: Migrate wire_* from wiring_system.py

**Files:**
- Modify: `app/bootstrap_components/wiring_system.py`

`wire_user_services` instantiates 9 services at once — split into individual `register_factory` entries. `wire_collaboration_module`, `wire_collaboration_services` need session_factory — keep as `register_factory`.

- [ ] **Step 1: Convert wires (dispatch to subagent for this batch)**

- [ ] **Step 2: Keep deprecated shims**

- [ ] **Step 3: Run tests**

### Task 1.4: Update service_wiring.py imports

**Files:**
- Modify: `app/bootstrap_components/service_wiring.py:433-511`

The module imports ~55 wire_* functions from wiring_market/ai/trading/system. After converting each:
- Remove the imports (or keep for deprecated shim calls)
- Remove `global _injector` from wiring_*.py files

- [ ] **Step 1: Replace wire_* imports with register_factory calls**

Where `service_wiring.py` does:
```python
from app.bootstrap_components.wiring_market import (
    wire_investment_manager_service,
    wire_moments_service,
    ...
)
```

Replace with:
```python
# Investment manager and moments need settings/session_factory — register as factories
register_factory("investment_manager_service", lambda reg: _make_investment_manager_service(reg))
register_factory("moments_service", lambda reg: _make_moments_service(reg))
# ... etc
```

- [ ] **Step 2: Remove wire_* imports, keep shim imports only**

- [ ] **Step 3: Run tests**

---

## SPRINT 2: Migrate complex services (register_factory pattern)

These services need dependency resolution from other registered services. Convert each to `register_factory` with explicit `reg.get()` calls.

### Task 2.0: Migrate ai_analysis_service and dependent services

**Files:**
- Modify: `app/bootstrap_components/service_wiring.py`

Current factory (already in place):
```python
def _make_ai_analysis_service(reg):
    from app.modules.ai_agent.services.ai_analysis_service import AiAnalysisService
    from app.infrastructure.adapters.ai_analysis_port_adapter import AiAnalysisPortAdapter
    stock = reg.get("stock_service")
    return AiAnalysisService(
        stock_service=stock,
        ai_adapter=AiAnalysisPortAdapter(),
        system_health_banner_service=reg.get("system_health_banner_service"),
    )
```

This is already correct. Audit all existing `_make_*` factories and convert any remaining inline wire functions.

- [ ] **Step 1: Audit and convert all remaining _make_* factories in service_wiring.py**

- [ ] **Step 2: Ensure each factory uses reg.get() for dependencies**

### Task 2.1: Migrate services needing settings/session_factory

Services like `investment_manager_service`, `moments_service`, `kronos_service`, `signal_observation_service`, `ten_kings_sniper_service`, `fingpt_application_service` need special factory functions.

- [ ] **Step 1: Create factory functions that accept (settings, session_factory) from registry config**

```python
def _make_investment_manager_service(reg):
    from app.application.services.portfolio.investment_manager_service import InvestmentManagerService
    from app.infrastructure.repositories.deps import create_investment_manager_repository
    from app.config import get_settings
    settings = get_settings()
    sf = getattr(reg, "_session_factory", None)
    repo = create_investment_manager_repository(settings, session_factory=sf)
    return InvestmentManagerService(repository=repo)
```

- [ ] **Step 2: Register via register_factory()**

- [ ] **Step 3: Run tests**

---

## SPRINT 3: Eliminate bind/get proxies (Phase 1c)

This is the largest migration — converting consumers from `get_*()` calls to constructor injection.

### Task 3.0: Audit all consumers (re-run audit)

**Files:**
- Run: `python scripts/audit_bind_get_usage.py`
- Output: `instance/bind_get_audit_sprint3.txt`

### Task 3.1: Migrate data services (highest impact group)

**Files to modify (consumers):**
- `app/application/services/data/data_router_service.py`
- `app/application/services/data/basic_market_data_service.py`
- `app/application/services/data/tdx_ohlcv_reader.py`
- `app/application/services/data/tdx_dayk_sync_service.py`
- `app/application/services/data/tdx_base_data_service.py`
- `app/application/services/data/pytdx_market_data_service.py`
- `app/application/services/data/cn_realtime_quote_service.py`

**Files to modify (helpers):**
- `app/application/services/helpers/tdx_data_repository_access.py`
- `app/application/services/helpers/tdx_local_access.py`
- `app/application/services/helpers/tdx_block_repository_access.py`
- `app/application/services/helpers/timescale_bar_access.py`
- `app/application/services/helpers/pytdx_access.py`
- `app/application/services/helpers/data_quality_access.py`
- `app/application/services/helpers/longhu_mapping_access.py`
- `app/application/services/helpers/config_loader_access.py`

**Migration pattern:**
```python
# Before (in data_router_service.py):
from app.application.services.helpers.tdx_local_access import get_tdx_local_file_port
class MarketDataService:
    def __init__(self, config):
        self._tdx_adapter = get_tdx_local_file_port().create_history_adapter(...)

# After:
class MarketDataService:
    def __init__(self, tdx_local_port: TdxLocalFilePort, config):
        self._tdx_adapter = tdx_local_port.create_history_adapter(...)
```

Then in service_wiring.py:
```python
register_factory("basic_market_data_service", lambda reg: _make_basic_market_data_service(reg))
```

Where `_make_basic_market_data_service` resolves the port from registry.

- [ ] **Step 1: Convert data_router_service.py to constructor injection** (dispatch to subagent)

- [ ] **Step 2: Convert basic_market_data_service.py** (dispatch to subagent)

- [ ] **Step 3: Convert remaining data services** (dispatch to subagent)

- [ ] **Step 4: Update binding functions — keep deprecated but add warning logs**

### Task 3.2: Migrate module context wires

**Files to modify:**
- `app/modules/market_data/module.py`
- `app/modules/ai_agent/module.py`
- `app/modules/portfolio_risk/module.py`
- `app/modules/strategy/module.py`
- `app/modules/execution/module.py`
- `app/modules/collaboration/module.py`
- `app/modules/mesh/module.py`
- `app/modules/perception/module.py`
- `app/modules/system/module.py`
- `app/modules/user/module.py`
- `app/modules/data/module.py`
- `app/modules/portfolio/module.py`
- `app/modules/research/module.py`
- `app/modules/misc/module.py`

Each module.py has inline `_init_*_service()` functions calling `get_*()` from helpers. Convert these to use registry lookups:

```python
# Before:
from app.application.services.helpers.market_data_provider import get_market_data_provider
market_provider = get_market_data_provider()

# After (in module initialize/wire method):
def initialize(container):
    from app.bootstrap_components.service_wiring import _get_registry
    reg = _get_registry()
    market_provider = reg.get("market_data_provider")
    ...
```

- [ ] **Step 1: Convert market_data/module.py** (dispatch to subagent)

- [ ] **Step 2: Convert remaining modules** (dispatch to subagent)

### Task 3.3: Migrate application services using helpers

**Files:**
- `app/application/services/tool_facade_service.py`
- `app/application/handlers/market_data/ingest_handler.py`
- `app/application/event_publisher.py`
- `app/application/events/handlers.py`
- `app/application/services/engine.py`
- `app/application/services/alpha/factor_performance_engine.py`
- `app/application/services/system/task_feedback_service.py`
- `app/application/services/system/memory_optimization_service.py`
- `app/application/services/system/alert_center_service.py`
- `app/application/services/strategy/strategy_service.py`
- `app/application/services/sentinel/agent_telemetry_service.py`
- `app/application/services/qlib/qlib_pipeline_service.py`
- `app/application/services/integration/integration_stack_service.py`
- `app/application/services/research/rdagent_run_service.py`

Same pattern — replace `get_*()` with constructor params.

- [ ] **Step 1: Migrate tool_facade_service.py** (dispatch to subagent — heavy consumer)

- [ ] **Step 2: Migrate remaining services** (dispatch to subagent)

### Task 3.4: Migrate presentation layer consumers

**Files:**
- `app/presentation/api/routes_v2.py`
- `app/presentation/api/routes_v1_retail_assistant.py`

```python
# Before:
from app.application.services.helpers.user_access import get_user_port
user = get_user_port()

# After:
# Route receives user_service from context
```

- [ ] **Step 1: Migrate routes_v2.py** (dispatch to subagent)

- [ ] **Step 2: Migrate routes_v1_retail_assistant.py**

### Task 3.5: Migrate domain layer consumers

**Files:**
- `app/domain/regime/__init__.py`
- `app/domain/regime/regime_strategy.py`
- `app/domain/alpha/regime_risk_budget.py`
- `app/infrastructure/timeseries/timeseries_factory.py`

Domain layer should NOT depend on application helpers. These need to receive ports via constructor or use the ServiceRegistry directly.

```python
# Before:
from app.application.services.helpers.regime_access import get_regime_port
port = get_regime_port()

# After:
from app.domain.ports.regime_port import RegimePort
class RegimeStrategy:
    def __init__(self, regime_port: RegimePort):
        self._port = regime_port
```

- [ ] **Step 1: Migrate regime layer** (dispatch to subagent)

### Task 3.6: Migrate Celery task consumers

**Files:**
- `app/tasks/task_wiring.py`
- `app/tasks/headline_signal_tasks.py`

- [ ] **Step 1: Migrate task_wiring.py** (dispatch to subagent)

### Task 3.7: Migrate remaining consumers

**Files:**
- `app/agents/research/integrated_graph.py`
- `app/application/trading/bot_engine.py`
- `app/application/use_cases/strategy_copilot_use_case.py`
- `app/modules/market_data/services/market_service.py`
- `app/modules/market_data/services/hot_sector_service.py`
- `app/modules/portfolio_risk/services/portfolio_trade_service.py`
- `app/modules/portfolio_risk/services/portfolio_market_service.py`

- [ ] **Step 1: Migrate remaining consumers** (dispatch to subagent)

---

## SPRINT 4: Decommission bind/get helpers (Phase 4 — partial)

### Task 4.0: Convert all *_wiring.py modules to deprecated shims

**Files (36 files):**
All `app/application/services/helpers/*_wiring.py`

Each file currently has:
```python
_port: SomePort | None = None
def bind_some_port(port): global _port; _port = port
def get_some_port(): return _port
```

Replace with deprecated wrappers:
```python
"""DEPRECATED: This module implements the legacy bind/get DI pattern.
Use ServiceRegistry (Phase 2) instead. This module will be removed.
"""
import warnings

def get_some_port():
    warnings.warn(
        "get_some_port() is deprecated. Migrate to ServiceRegistry.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise RuntimeError("SomePort not available via deprecated bind/get. Use ServiceRegistry.")
```

- [ ] **Step 1: Generate and apply deprecation stubs for all 36 wiring files** (dispatch to subagent)

### Task 4.1: Convert *_access.py modules to deprecated re-exports

**Files (37 files):**
All `app/application/services/helpers/*_access.py`

These already do `from *_wiring import *`. Change to:
```python
"""DEPRECATED: Use ServiceRegistry instead."""
import warnings
warnings.warn(
    "*_access modules are deprecated. Migrate to ServiceRegistry.",
    DeprecationWarning,
    stacklevel=2,
)
# Re-export deprecated functions (they now raise with warning)
from *_wiring import *
```

- [ ] **Step 1: Update all 37 *_access.py files** (dispatch to subagent)

### Task 4.2: Remove bind_application_infrastructure() calls

**Files:**
- `app/bootstrap_components/infrastructure_binding.py`
- `app/bootstrap_components/services.py` (line 281: `bind_application_infrastructure(s)`)

Remove the call from `Services.__init__`. All ports are now resolved from ServiceRegistry.

- [ ] **Step 1: Remove bind call from services.py**

- [ ] **Step 2: Deprecate infrastructure_binding.py**

- [ ] **Step 3: Run full test suite**

### Task 4.3: Remove global _bound flag

**Files:**
- `app/bootstrap_components/infrastructure_binding.py:9`

- [ ] **Step 1: Remove the `_bound` global**

### Task 4.4: Remove _registry global from service_wiring.py

**Files:**
- `app/bootstrap_components/service_wiring.py:39`

Replace `global _registry` with injecting the registry instance.

---

## SPRINT 5: Split create_app() (Phase 3)

### Task 5.0: Extract configuration functions from create_app()

**Files:**
- Create: `app/bootstrap_components/configure_flask.py`
- Create: `app/bootstrap_components/configure_database.py`
- Create: `app/bootstrap_components/configure_registry.py`
- Create: `app/bootstrap_components/configure_services.py`
- Create: `app/bootstrap_components/configure_presentations.py`
- Create: `app/bootstrap_components/configure_extensions.py`

```python
# configure_flask.py
def configure_flask_app(settings):
    """Create and configure the base Flask app."""
    from pathlib import Path
    from flask import Flask
    from .config import get_settings
    settings = settings or get_settings()
    app = Flask(
        __name__,
        template_folder=settings.template_folder,
        static_folder=settings.static_folder,
    )
    app.config.from_object(settings)
    if not settings.secret_key:
        from app.domain.exceptions import CriticalSecurityError
        raise CriticalSecurityError("secret_key not configured", {"env_var": "SECRET_KEY"})
    app.secret_key = settings.secret_key
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("REMEMBER_COOKIE_SAMESITE", "Lax")
    # ... i18n, context processor, security headers, request middleware
    return app
```

Similar for each module. Each is independently testable.

- [ ] **Step 1: Create configure_flask.py** (dispatch to subagent)

- [ ] **Step 2: Create configure_database.py**

- [ ] **Step 3: Create configure_registry.py**

- [ ] **Step 4: Create configure_services.py**

- [ ] **Step 5: Create configure_presentations.py**

- [ ] **Step 6: Create configure_extensions.py**

### Task 5.1: Rewrite create_app() as composition

**Files:**
- Modify: `app/bootstrap.py`

```python
def create_app(*, settings=None, config=None):
    app = configure_flask_app(settings)
    configure_database(app, settings)
    configure_registry(app, config or {})
    configure_services(app, settings)
    configure_presentations(app, settings)
    configure_extensions(app, settings)
    validate_runtime_config(get_settings())
    return app
```

- [ ] **Step 1: Rewrite create_app()**

- [ ] **Step 2: Write tests for each configuration function**

- [ ] **Step 3: Run full test suite**

---

## SPRINT 6: Simplify Services class (Phase 4 continuation)

### Task 6.0: Remove __getattr__ fallback from Services class

**Files:**
- Modify: `app/bootstrap_components/services.py`

Remove the `__getattr__` method and all 100+ `= None` class attributes. Services are resolved via `@register_service` / `register_factory` only.

```python
# Before:
class Services:
    market_service = None
    stock_service = None
    # ... 100+ more
    def __getattr__(self, name):
        val = _get_registry().get(name, default=None)
        if val is not None:
            object.__setattr__(self, name, val)
            return val
        return None

# After:
class Services:
    """Services bundle — attributes resolved via register_factory / @register_service."""
    def __init__(self, registry):
        # Explicit attributes that need special construction
        self.market_service = registry.get("market_service")
        self.stock_service = registry.get("stock_service")
        # ... only explicit attributes, no __getattr__
```

- [ ] **Step 1: Audit which services need explicit vs implicit resolution**

- [ ] **Step 2: Rewrite Services.__init__ with explicit attributes**

- [ ] **Step 3: Remove __getattr__ and all `= None` class attributes**

- [ ] **Step 4: Run test suite**

### Task 6.1: Remove global _injector from wiring_*.py files

**Files:**
- `app/bootstrap_components/wiring_market.py`
- `app/bootstrap_components/wiring_ai.py`
- `app/bootstrap_components/wiring_trading.py`
- `app/bootstrap_components/wiring_system.py`

Each has `_injector: ServiceInjector | None = None`. These are no longer needed.

- [ ] **Step 1: Remove all _injector globals and import ServiceInjector**

---

## SPRINT 7: Clean up modules/ duplication (Phase 5)

This is the most open-ended phase — requires architectural decisions.

### Task 7.0: Map duplication inventory

**Files:**
- Audit which services exist in both `modules/*/services/` and `application/services/`
- Create: `docs/phase5-duplication-inventory.md`

- [ ] **Step 1: Document which services belong where**

Decisions to make:
- Services in `modules/*/services/` with `@register_module` = bounded context services (keep)
- Services in `application/services/` with CQRS structure = use-case services (keep)
- Services in both = pick one canonical location

- [ ] **Step 2: Create duplication inventory document**

### Task 7.1: Consolidate service locations

Based on the inventory, move duplicated services to their canonical location.

- [ ] **Step 1: Move ai_analysis_service to canonical location**

- [ ] **Step 2: Move market_data services**

- [ ] **Step 3: Move strategy services**

- [ ] **Step 4: Update all imports**

### Task 7.2: Remove deprecated shim from core/modules.py

**Files:**
- `app/core/modules.py`

Replace `module_manifest()` with `context_module_manifest()` as the only entrypoint.

- [ ] **Step 1: Clean up modules.py**

---

## Sprint ordering and dependencies

```
Sprint 0 → Sprint 1 → Sprint 2 → Sprint 3 → Sprint 4 → Sprint 5 → Sprint 6 → Sprint 7
```

Each sprint depends on all previous ones completing. Sprint 3 (consumer migration) is the largest — it touches ~50 consumer files across all layers.

---

## Risk mitigation

1. **Backward compat**: All deprecated functions log `DeprecationWarning` before raising. Consumers migrate at their own pace.
2. **Testing**: After each sprint, run `pytest tests/bootstrap/ tests/core/ tests/application/ -q` to catch regressions early.
3. **Rollback**: Each sprint's changes are self-contained and revertable. Keep the old code behind a `DEPRECATED` wrapper, not deleted.
4. **Celery workers**: After Sprint 4, Celery workers need the ServiceRegistry initialized. Add a note in `celery_app.py` to call `configure_service_registry()` at worker startup.

---

## Verification checklist (run after all sprints)

- [ ] `python scripts/audit_bind_get_usage.py` shows 0 consumers
- [ ] `pytest tests/ -q` passes
- [ ] `create_app()` starts successfully
- [ ] `create_app()` can be called with test config (no MySQL/Redis required)
- [ ] All `*_wiring.py` files log deprecation warnings
- [ ] All `*_access.py` files log deprecation warnings
- [ ] `app/bootstrap_components/services.py` has no `__getattr__` method
- [ ] `app/bootstrap_components/services.py` has no `= None` class attributes
- [ ] `app/bootstrap_components/service_wiring.py` has no `global _registry`
- [ ] `app/bootstrap_components/infrastructure_binding.py` has no `global _bound`
- [ ] `app/core/registry.py` has no module-level mutable dicts (move into ServiceRegistry instance)
- [ ] `app/bootstrap.py::create_app()` is < 50 lines (was 301)
