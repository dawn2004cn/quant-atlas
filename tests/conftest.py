"""Pytest configuration for Quant Atlas.

Fixes for pytest collection:
- Add project root to sys.path so ``import app.*`` works.
- Disable background services to avoid blocked threads on import.
- Register custom markers for test classification.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Project root — needed because tests/ lives next to app/ but pytest may not
# add the project root to sys.path on Windows.
# ---------------------------------------------------------------------------
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# ---------------------------------------------------------------------------
# Force lightweight cache/backend BEFORE any app module imports.
# ---------------------------------------------------------------------------
os.environ.setdefault("CACHE_BACKEND", "memory")
os.environ.setdefault("ENABLE_BACKGROUND_SCANNER", "0")
os.environ.setdefault("ENABLE_BASIC_DATA_SCHEDULER", "0")
os.environ.setdefault("TASK_MESSAGE_REDIS_URL", "memory://")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "memory://")
os.environ.setdefault("STRICT_BOOTSTRAP", "0")


# ---------------------------------------------------------------------------
# Custom markers
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line(
        "markers",
        "integration: mark test needing MySQL/Redis",
    )
    config.addinivalue_line("markers", "nightly: mark test for scheduled full-boot runs")
    config.addinivalue_line("markers", "qlib: mark test needing Qlib")
    config.addinivalue_line("markers", "agent: mark test importing LangGraph")


_SLOW_FIXTURES = frozenset({"flask_app", "client"})


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests that boot the full Flask app as slow."""
    for item in items:
        if _SLOW_FIXTURES.intersection(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.slow)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def flask_app():
    """Session-scoped Flask app for tests that need the full app."""
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["SERVER_NAME"] = "localhost"
    return app


@pytest.fixture
def client(flask_app):
    """Test client for individual tests."""
    with flask_app.test_client() as c:
        yield c
