# P4 Alpha Marketplace Route Dependency Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove repeated dynamic imports in Alpha Marketplace route handlers by resolving services through the registry first and falling back to explicit constructors only at helper boundaries.

**Architecture:** Keep route behavior and public endpoints unchanged. Move service resolution into `_get_svc()` and `_get_compliance()` using `_get_registry().get_or_none(...)`, so route handlers do not import services inline. Do not rewrite the marketplace service or compliance service.

**Tech Stack:** Python 3.12, pytest.

---

### Task 1: Normalize Alpha Marketplace route helpers

**Files:**
- Modify: `app/presentation/api/routes_v1_alpha_marketplace.py`
- Create: `tests/presentation/test_alpha_marketplace_route_helpers.py`

- [ ] **Step 1: Write failing test**

```python
from app.presentation.api import routes_v1_alpha_marketplace as routes

class Registry:
    def get_or_none(self, name):
        return {"svc" if name == "alpha_marketplace_service" else "compliance"}[name]

def test_route_helpers_prefer_registry(monkeypatch):
    monkeypatch.setattr(routes, "_get_registry", lambda: Registry())
    assert routes._get_svc() == "svc"
    assert routes._get_compliance() == "compliance"
```

Expected: FAIL because helpers currently instantiate services directly.

- [ ] **Step 2: Import registry accessor**

```python
from ...bootstrap_components.service_wiring import _get_registry
```

- [ ] **Step 3: Rewrite helpers**

```python
def _get_svc():
    svc = _get_registry().get_or_none("alpha_marketplace_service")
    if svc is not None:
        return svc
    from app.modules.system.services.alpha.alpha_marketplace_service import AlphaMarketplaceService
    return AlphaMarketplaceService(compliance_service=_get_compliance())

def _get_compliance():
    compliance = _get_registry().get_or_none("compliance_service")
    if compliance is not None:
        return compliance
    from app.modules.system.services.compliance_service import ComplianceService
    return ComplianceService()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/presentation/test_alpha_marketplace_route_helpers.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] Route handlers still call `_get_svc()` and `_get_compliance()`.
- [ ] Helpers prefer registry services.
- [ ] Fallback constructors remain available for local/test use.
- [ ] No endpoint path or response contract changes.
- [ ] No unrelated marketplace business logic changes.
