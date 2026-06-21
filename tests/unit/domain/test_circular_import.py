"""Tests for the circular import fix in domain/regime/regime_strategy.py.

Verifies that MarketRegime is no longer eagerly imported, which would
create a circular dependency chain:
  domain → regime → agents → research → graph → quant_tools →
  market_data → application → core.factory
"""

from __future__ import annotations

import sys

from app.domain import base, entities, enums
from app.domain.enums import MarketCode


class TestDomainNoCircularImports:
    """Verify domain layer imports do not trigger agent graph loading."""

    def test_import_domain_regime_without_agents(self):
        """Importing regime_strategy must not block or hang."""
        from app.domain.regime.regime_strategy import (
            RegimeParameters,
            RegimeTemplate,
            RegimeStrategySwitcher,
        )

        assert RegimeParameters is not None
        assert RegimeTemplate is not None
        assert RegimeStrategySwitcher is not None

    def test_import_domain_regime_does_not_import_agents(self, monkeypatch):
        """After importing domain.regime, agents.dynamic_personality should
        not have been imported implicitly."""
        imported_modules_before = set(sys.modules.keys())  # type: ignore[name-defined]

        from app.domain.regime.regime_strategy import (
            StressTestSimulator,
        )

        assert StressTestSimulator is not None

        # The agents package should NOT be in sys.modules yet
        agent_modules = [
            k for k in sys.modules if k.startswith("app.agents")
        ]
        assert (
            agent_modules == []
        ), f"Domain import pulled in agent modules: {agent_modules}"

    def test_import_full_domain(self):
        """import app.domain.* should not hang or error."""
        from app.domain import base, entities, enums

        assert base.Entity is not None
        assert entities.MarketSnapshot is not None
        assert enums.MarketCode is not None
