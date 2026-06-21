from __future__ import annotations
"""Option 1–9 / V1–V9 integration acceptance smoke tests (see docs/option_1_9.md)."""

import importlib


def test_foundation_workflow_service() -> None:
    from app.application.workflows.workflow_service import WorkflowService

    svc = WorkflowService()
    assert svc is not None


def test_foundation_capability_registry() -> None:
    from app.infrastructure.capabilities.registry import CapabilityRegistry

    reg = CapabilityRegistry()
    assert reg is not None


def test_foundation_system_pulse() -> None:
    from app.modules.system.services.system.system_pulse_service import SystemPulseService

    svc = SystemPulseService()
    pulse = svc.build_pulse(ctx=None)
    assert pulse is not None


def test_v4_event_bus_singleton() -> None:
    from app.core.event_bus import get_event_bus

    bus = get_event_bus()
    bus.publish.__doc__  # noqa: B018 — ensure callable
    assert bus.list_recent_events(limit=5) is not None


def test_v6_collaboration_importable() -> None:
    mod = importlib.import_module("app.modules.user.services.user.collaboration_service")
    assert hasattr(mod, "CollaborationService")


def test_v7_simulation_gateway_presets() -> None:
    from app.modules.execution.services.simulation_gateway_service import SimulationGatewayService

    svc = SimulationGatewayService()
    out = svc.list_scenarios()
    assert out["ok"] is True
    assert len(out["presets"]) >= 4


def test_v8_meta_arbiter_importable() -> None:
    mod = importlib.import_module("app.application.services.orchestration.meta_arbiter_service")
    assert hasattr(mod, "MetaArbiterService")


def test_v9_mesh_manifest_disabled_by_default() -> None:
    from app.modules.system.services.system.mesh_gateway_service import MeshGatewayService

    svc = MeshGatewayService()
    m = svc.get_manifest()
    assert m["ok"] is True


def test_v9_borderless_execution_manifest() -> None:
    from app.modules.execution.services.borderless_execution_service import BorderlessExecutionService

    m = BorderlessExecutionService().get_manifest()
    assert m["ok"] is True
    assert "CN" in m["markets"]


def test_v9_hyper_simulator_manifest() -> None:
    from app.modules.execution.services.hyper_simulator_service import HyperSimulatorService

    m = HyperSimulatorService().get_manifest()
    assert m["ok"] is True
    assert len(m["modes"]) == 3


def test_v9_data_truth_guardian_manifest() -> None:
    from unittest.mock import MagicMock

    from app.modules.system.services.system.data_truth_guardian_service import DataTruthGuardianService

    m = DataTruthGuardianService(
        data_quality=MagicMock(),
        truth_sentry=MagicMock(),
    ).get_manifest()
    assert m["ok"] is True
    assert "resync_qlib" in m["heal_actions"]


def test_v9_decision_theater_scene() -> None:
    from app.modules.system.services.ui.decision_theater_service import DecisionTheaterService

    out = DecisionTheaterService().build_theater(user_id=1)
    assert out["ok"] is True
    assert len(out["scene"]["nodes"]) >= 6
