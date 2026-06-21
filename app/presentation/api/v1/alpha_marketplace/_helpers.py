"""Service accessors for alpha marketplace HTTP routes."""

from __future__ import annotations

from typing import Any

from app.bootstrap_components.service_wiring import _get_registry


def get_marketplace_service() -> Any:
    svc = _get_registry().get_or_none("alpha_marketplace_service")
    if svc is not None:
        return svc
    from app.modules.system.services.alpha.alpha_marketplace_service import AlphaMarketplaceService

    return AlphaMarketplaceService(compliance_service=get_compliance_service())


def get_compliance_service() -> Any:
    compliance = _get_registry().get_or_none("compliance_service")
    if compliance is not None:
        return compliance
    from app.modules.system.services.compliance_service import ComplianceService

    return ComplianceService()
