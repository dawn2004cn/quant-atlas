from __future__ import annotations

from app.modules.system.services.mesh.manifest_service_10 import ManifestService10


def test_manifest_service_10_import_and_manifest() -> None:
    svc = ManifestService10(registry=None)
    manifest = svc.get_manifest()
    assert manifest["ok"] is True
    assert manifest["version"] == "10.0"
    assert "components" in manifest
    assert manifest["summary"]["total"] >= 1


def test_manifest_service_10_unknown_component() -> None:
    svc = ManifestService10(registry=None)
    detail = svc.get_component_detail("not_a_real_component")
    assert detail["ok"] is False


def test_perception_resonance_service_stats() -> None:
    from app.modules.system.services.mesh.perception_resonance_service import (
        PerceptionResonanceService,
        ResonanceActionEvent,
        ResonanceTriggeredResearchEvent,
    )

    svc = PerceptionResonanceService(perception_layer=None)
    stats = svc.get_stats()
    assert stats["ok"] is True
    assert stats["enabled"] is False
    assert svc.get_action_log(limit=10) == []
    assert ResonanceActionEvent.__name__ == "ResonanceActionEvent"
    assert ResonanceTriggeredResearchEvent.__name__ == "ResonanceTriggeredResearchEvent"
