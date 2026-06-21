"""Tests for service module preloading and registry wiring."""

from __future__ import annotations

from types import SimpleNamespace

from app.bootstrap_components.service_loader import preload_service_modules
from app.bootstrap_components.service_wiring import (
    configure_service_registry,
    rewire_infra_dependent_services,
)
from app.core.registry import registered_service_names, wire_from_registry


def test_preload_service_modules_populates_registry():
    before = set(registered_service_names())
    loaded = preload_service_modules()
    after = set(registered_service_names())

    assert loaded > 0
    assert after >= before
    assert "memory_optimization_service" in after
    assert "task_pipeline_service" in after
    assert "investment_committee_service" in after
    assert "rdagent_run_service" in after
    assert "evidence_graph_service" in after
    assert "user_access_policy_service" in after
    assert "user_decision_context_service" in after


def test_wire_from_registry_injects_memory_and_pipeline_after_infra_bind():
    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings

    preload_service_modules()
    configure_service_registry({})
    bind_application_infrastructure(get_settings())
    services = SimpleNamespace(
        memory_optimization_service=None,
        task_pipeline_service=None,
        investment_committee_service=None,
        rdagent_run_service=None,
        evidence_graph_service=None,
        user_access_policy_service=None,
        user_decision_context_service=None,
        factor_orthogonalization_service=None,
        factor_self_correction_service=None,
        industry_chain_service=None,
        data_infrastructure_service=None,
        tdx_base_read_service=None,
        gpcw_service=None,
    )
    wire_from_registry(services)

    assert services.memory_optimization_service is not None
    assert services.task_pipeline_service is not None
    assert services.investment_committee_service is not None
    assert services.rdagent_run_service is not None
    assert services.evidence_graph_service is not None
    assert services.user_access_policy_service is not None
    assert services.user_decision_context_service is not None
    assert services.factor_orthogonalization_service is not None
    assert services.factor_self_correction_service is not None
    assert services.industry_chain_service is not None
    assert services.data_infrastructure_service is not None
    assert services.tdx_base_read_service is not None
    assert services.gpcw_service is not None


def test_rewire_infra_dependent_services_refreshes_gpcw():
    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
    from app.config import get_settings

    preload_service_modules()
    configure_service_registry({})
    services = SimpleNamespace(gpcw_service=object())
    bind_application_infrastructure(get_settings())
    rewire_infra_dependent_services(services)
    from app.modules.data.services.gpcw_service import GpcwApplicationService

    assert isinstance(services.gpcw_service, GpcwApplicationService)
