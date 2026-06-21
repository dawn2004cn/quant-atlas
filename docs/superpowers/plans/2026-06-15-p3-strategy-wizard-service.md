# P3 Strategy Wizard Service Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the nested StrategyWizardService used by the wizard API reliable and registry-safe without merging it into the root marketplace-style service.

**Architecture:** Keep the API route importing `app.modules.strategy.services.strategy.strategy_wizard_service.StrategyWizardService`. Fix its missing logger and optional dependency resolution so missing optional services do not crash route registration or calls. Do not delete the root strategy wizard service in this batch.

**Tech Stack:** Python 3.12, pytest.

---

### Task 1: Fix nested StrategyWizardService dependencies

**Files:**
- Modify: `app/modules/strategy/services/strategy/strategy_wizard_service.py`
- Create: `tests/modules/strategy/test_strategy_wizard_service_nested.py`

- [ ] **Step 1: Write failing test**

```python
from app.modules.strategy.services.strategy.strategy_wizard_service import StrategyWizardService

class Registry:
    def get(self, name): raise KeyError(name)
    def get_or_none(self, name): return None

def test_wizard_service_starts_without_optional_registry_entries():
    service = StrategyWizardService(Registry())
    data = service.get_wizard_start_data()
    assert data["templates"]
```

Expected: FAIL because logger is undefined and required dependencies are resolved with `get()`.

- [ ] **Step 2: Add logger import**

```python
from app.core.logger import get_logger
logger = get_logger(__name__)
```

- [ ] **Step 3: Use optional dependency lookup**

```python
self.backtest_service = registry.get_or_none("strategy_optimization_service")
self.strategy_risk_validator = registry.get_or_none("strategy_risk_validator")
```

- [ ] **Step 4: Keep required dependencies explicit**

```python
self.strategy_service = registry.get("strategy_service")
self.fast_engine = registry.get("fast_backtest_engine")
```

- [ ] **Step 5: Guard risk validator call**

```python
risk_validator = getattr(self, "strategy_risk_validator", None)
if risk_validator:
    ...
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/modules/strategy/test_strategy_wizard_service_nested.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] Nested wizard service imports logger before using it.
- [ ] Optional registry entries use `get_or_none`.
- [ ] Missing optional services do not crash `get_wizard_start_data`.
- [ ] API route import target remains unchanged.
- [ ] Root `app/modules/strategy/services/strategy_wizard_service.py` is not deleted or merged.
