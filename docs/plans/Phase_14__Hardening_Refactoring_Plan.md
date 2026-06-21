# Phase 14 Implementation Plan: Hardening - Global Constant Extraction & Configuration Refactoring

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.
>
**Goal:** Systematically replace all hardcoded, magic constants (like subnet masks, fixed IPs, arbitrary thresholds) with configuration variables read from a centralized `app/config/settings.py` or environment variable lookup. This increases portability and maintainability across the codebase.

**Architecture:** Global Config Layering. Establish a set of required settings in the central config module (`app/config/settings.py`), then use that single source to overwrite local hardcoded values throughout 5+ modules.
**Tech Stack:** Python, `python-dotenv` (or equivalent config loader).

---

### Task 1: Core Configuration Infrastructure Setup (The Source of Truth)

**Files:**
*   Modify: `app/config/settings.py` (Create the central place for constants)
*   Test: `tests/unit/config_test.py` (Validate default loading)

**Step 1.1: Write the failing test to enforce config centralization.**
We will write a test that initially fails because it tries to access a hardcoded value (e.g., an IP or mask) which should *now* come from settings, and force its definition into `settings.py` stubbed for this task.

```python
# tests/unit/config_test.py
def test_default_subnet_mask_is_loaded():
    # Test that the service correctly loads IP masks instead of using a local default value.
    from app.config.settings import DEFAULT_NETWORK_MASK
    assert DEFAULT_NETWORK_MASK == "122.0.0.0/8" # Assuming this is the desired config default
```

**Step 1.2: Update `app/config/settings.py` stub.**
Define a variable to hold common network constants.

`app/config/settings.py`: (Add new constant)
```python
# ... other settings ...
# Phase 14 Mandatory Configs: Network Constants
DEFAULT_NETWORK_MASK = "122.0.0.0/8"
PORTFOLIO_INITIAL_CAPITAL = 500000.0 # Example of a hardcoded number replacement
```

**Step 1.3: Test Configuration Loading.**
Run the newly stubbed test to ensure successful loading path from `settings.py`.

---

### Task 2: Network Constant Injection (Example: Subnet Masks)

**Goal:** Eliminate hardcoded subnet masks (`122.0.0.0`, `134.0.0.0`) across multiple service modules, replacing them with the centralized setting.
**Files:**
*   Modify: `app/core/networking_utils.py` (A common utility module, if one exists)
*   Modify: `app/modules/financial_data/market_data.py` (Example target 1)

**Step 2.1: Identify and Replace.**
Systematically find all instances of hardcoded network masks in the identified files and replace them with calls to `settings.DEFAULT_NETWORK_MASK`.

---

### Task 3: Hardcoded Protocol Values Cleanup (Example: Timeout/Retry Counts)

**Goal:** Centralize non-business logic 'magic numbers' like timeouts, retry limits, or failure thresholds into a readable config dictionary in the settings module.
**Files:**
*   Modify: `app/core/circuit_breaker.py` (Uses hardcoded retry counts/timeouts).
*   Modify: `app/modules/system/data_fetcher.py` (If such a standard fetching layer exists).

This plan completes the transition from massive feature-building stubs to necessary operational hardening tasks. Proceeding with this structured approach is the correct logical next step after Phase 13.