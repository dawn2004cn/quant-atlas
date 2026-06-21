from __future__ import annotations

from app.modules.strategy.services.strategy.strategy_wizard_service import StrategyWizardService


class _FakeRegistry:
    def get(self, name):
        return object()

    def get_or_none(self, _name):
        return None


def test_wizard_service_starts_without_optional_registry_entries():
    service = StrategyWizardService(_FakeRegistry())

    data = service.get_wizard_start_data()

    assert data["templates"]
    assert data["categories"]
    assert "recommendation" in data
