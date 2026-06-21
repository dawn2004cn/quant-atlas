from __future__ import annotations

from app.presentation.api import routes_v1_alpha_marketplace as routes


class _FakeRegistry:
    def __init__(self, values):
        self.values = values

    def get_or_none(self, name):
        return self.values.get(name)


def test_route_helpers_prefer_registry(monkeypatch):
    monkeypatch.setattr(routes, "_get_registry", lambda: _FakeRegistry({
        "alpha_marketplace_service": "svc",
        "compliance_service": "compliance",
    }))

    assert routes._get_svc() == "svc"
    assert routes._get_compliance() == "compliance"


def test_route_helpers_fall_back_to_constructors(monkeypatch):
    calls = []

    class FakeSvc:
        pass

    class FakeCompliance:
        pass

    def fake_registry():
        return _FakeRegistry({})

    def fake_alpha(*args, **kwargs):
        calls.append(("alpha", args, kwargs))
        return "svc"

    def fake_compliance():
        calls.append(("compliance",))
        return "compliance"

    monkeypatch.setattr(routes, "_get_registry", fake_registry)
    monkeypatch.setattr("app.modules.system.services.alpha.alpha_marketplace_service.AlphaMarketplaceService", fake_alpha)
    monkeypatch.setattr("app.modules.system.services.compliance_service.ComplianceService", fake_compliance)

    assert routes._get_svc() == "svc"
    assert routes._get_compliance() == "compliance"
    assert calls == [
        ("compliance",),
        ("alpha", (), {"compliance_service": "compliance"}),
        ("compliance",),
    ]
