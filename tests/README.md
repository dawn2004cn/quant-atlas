# Test Suite

## Structure

```
tests/
  conftest.py                        # Global pytest config, fixtures
  unit/                              # Unit tests (no external deps)
    domain/
      test_base.py                   # Entity, ValueObject, AggregateRoot
      test_entities.py               # Domain entities (MarketSnapshot, etc.)
      test_enums.py                  # Domain enums (MarketCode, etc.)
      test_circular_import.py        # Verify domain→agent circular import fix
  scripts/                           # Legacy scripts (needs migration)
  agents/                            # Agent tests
  test_*.py                          # Flat test files (mixed quality, being migrated)
```

## Running Tests

```bash
# Run all tests (only files that can be imported)
pytest

# Run only unit tests (fast, no external deps)
pytest tests/unit/

# Run a specific file
pytest tests/unit/domain/test_base.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing tests/unit/

# Skip slow/integration tests
pytest -m "not slow and not integration"
```

## Test Writing Guidelines

1. **Domain tests** — pure logic, no Flask, no DB, no network. Import from `app.domain.*` only.
2. **Application tests** — mock infrastructure ports. Never import `infrastructure.*` directly.
3. **Integration tests** — mark with `@pytest.mark.integration`. Need MySQL/Redis running.
4. **Agent tests** — mark with `@pytest.mark.agent`. May be slow.
5. **No imports of `infrastructure.*`** in unit tests. Use ports and mocks.
6. **No imports of `presentation.*`** in unit or application tests.

## Current Status

| Category | Files | Tests | Status |
|----------|-------|-------|--------|
| Unit Domain | 4 | 69 | ✅ Green |
| Existing Working | ~50 | ~130 | ⚠️ Mixed (some have stale imports) |
| Failing Import | ~40 | — | ❌ Broken (circular imports, stale `services/` refs) |

## Migrating Broken Tests

Tests that fail with `ImportError` during collection typically:
1. Import from stale `services/` module (old location, renamed to `application/services/`)
2. Trigger the domain→agent circular import chain
3. Need infrastructure (MySQL/Redis) that's not available

To fix: update imports to use `app.domain.*`, `app.application.*`, `app.infrastructure.*` correctly, and use mocks for infrastructure.
