"""Execution service wiring — investment manager, trade execution."""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_factory

logger = logging.getLogger(__name__)


def _make_investment_manager_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.infrastructure.repositories.deps import (
        create_investment_manager_repository,
        create_signal_flag_pool_repository,
        create_stock_cache,
    )
    from app.modules.execution.services.investment_manager_service import InvestmentManagerService
    settings = get_settings()
    sf = getattr(reg, "_session_factory", None)
    repo = create_investment_manager_repository(settings, session_factory=sf)
    return InvestmentManagerService(
        repo,
        stock_cache=create_stock_cache(),
        signal_flag_pool=create_signal_flag_pool_repository(settings),
    )


register_factory("investment_manager_service", _make_investment_manager_service)
