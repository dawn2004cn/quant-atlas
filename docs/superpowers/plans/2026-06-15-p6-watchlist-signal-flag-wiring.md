# P6 Watchlist/Signal Flag Service Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the portfolio/watchlist-related services that routes already expect, so `watchlist_agent_service`, `watchlist_experience_service`, and `signal_flag_service` resolve through the service registry instead of returning `None`.

**Architecture:** Add three registry factories in `wiring_market.py`. Each factory uses already-wired dependencies (`watchlist_service`, `stock_group_service`, `market_service`, `stock_service`, `stock_cache`, `signal_flag_pool`). Do not change route contracts.

**Tech Stack:** Python 3.12, ServiceRegistry factories.

---

### Task 1: Register watchlist and signal flag factories

**Files:**
- Modify: `app/bootstrap_components/wiring_market.py`
- Create: `tests/bootstrap/test_watchlist_signal_flag_wiring.py`

- [ ] **Step 1: Write failing test**

```python
from app.bootstrap_components.wiring_market import _make_watchlist_agent_service, _make_watchlist_experience_service, _make_signal_flag_service

class Reg:
    def get(self, name): return object()
    def get_or_none(self, name): return None

def test_watchlist_factories_return_services():
    assert _make_watchlist_agent_service(Reg()).build_snapshot is not None
    assert _make_watchlist_experience_service(Reg()).dashboard is not None
    assert _make_signal_flag_service(Reg()).run_scan is not None
```

Expected: FAIL because factory functions do not exist.

- [ ] **Step 2: Add factories after `_make_watchlist_service`**

```python
def _make_watchlist_agent_service(reg):
    from app.modules.market_data.services.watchlist_agent_service import WatchlistAgentService
    return WatchlistAgentService(
        market_service=reg.get("market_service"),
        stock_service=reg.get("stock_service"),
        watchlist_service=reg.get("watchlist_service"),
        stock_group_service=reg.get("stock_group_service"),
    )

register_factory("watchlist_agent_service", _make_watchlist_agent_service)
```

- [ ] **Step 3: Add watchlist experience factory**

```python
def _make_watchlist_experience_service(reg):
    from app.modules.market_data.services.watchlist_experience_service import WatchlistExperienceService
    return WatchlistExperienceService(
        watchlist_agent_service=reg.get("watchlist_agent_service"),
        review_tracking_service=reg.get_or_none("review_tracking_service"),
    )

register_factory("watchlist_experience_service", _make_watchlist_experience_service)
```

- [ ] **Step 4: Add signal flag factory**

```python
def _make_signal_flag_service(reg):
    from app.config import get_settings
    from app.infrastructure.repositories.deps import create_signal_flag_pool_repository
    from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
    settings = get_settings()
    return SignalFlagScannerService(
        stock_service=reg.get("stock_service"),
        stock_cache=reg.get("stock_cache"),
        repository=create_signal_flag_pool_repository(settings),
        enable_qlib=bool(getattr(settings, "enable_qlib", False)),
    )

register_factory("signal_flag_service", _make_signal_flag_service)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/bootstrap/test_watchlist_signal_flag_wiring.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] Factories use registry dependencies, not new global singletons.
- [ ] Optional review service uses `get_or_none`.
- [ ] `signal_flag_service` can resolve when `stock_cache` and repository exist.
- [ ] No route path or response contract changes.
- [ ] No unrelated service wiring changes.
