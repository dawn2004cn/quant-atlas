from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""GPCW Financial Data Service — delegates to ``TdxGpcwRepository`` Port."""


import logging
from typing import Any

from app.core.registry import register_service
from app.domain.ports.tdx_gpcw_port import TdxGpcwRepository


logger = logging.getLogger(__name__)
_tdx_gpcw_repository: TdxGpcwRepository | None = None
_gpcw_service: GpcwApplicationService | None = None


def bind_tdx_gpcw_repository(repository: TdxGpcwRepository) -> None:
    """Bind the infrastructure repository used by GPCW services."""
    global _tdx_gpcw_repository, _gpcw_service
    _tdx_gpcw_repository = repository
    _gpcw_service = None


def _repository() -> TdxGpcwRepository:
    global _tdx_gpcw_repository
    if _tdx_gpcw_repository is None:
        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import create_tdx_gpcw_repository

        _tdx_gpcw_repository = create_tdx_gpcw_repository(get_settings())
    return _tdx_gpcw_repository


@register_service(name="gpcw_service")
class GpcwApplicationService:
    """Application service for GPCW financial data."""

    def __init__(self, repository: TdxGpcwRepository | None = None):
        self._repo = repository or _repository()

    def get_stock_periods(self, code: str) -> list[dict[str, Any]]:
        """Get available reporting periods for a stock."""
        try:
            return self._repo.get_stock_periods(code)
        except Exception as e:
            logger.error(f"GpcwService.get_stock_periods failed for {code}: {e}")
            return []

    def get_stock_data(self, code: str, report_date: int) -> GenericResponseDTO | None:
        """Get financial data for a specific reporting period."""
        try:
            return self._repo.get_stock_data(code, report_date)
        except Exception as e:
            logger.error(f"GpcwService.get_stock_data failed for {code}/{report_date}: {e}")
            return None

    def get_stock_data_by_indexed_code(
        self, indexed_code: str, report_date: int
    ) -> GenericResponseDTO | None:
        """Get financial data by indexed code."""
        try:
            return self._repo.get_stock_data_by_indexed_code(indexed_code, report_date)
        except Exception as e:
            logger.error(f"GpcwService.get_stock_data_by_indexed_code failed: {e}")
            return None

    def table_exists(self) -> bool:
        """Check if GPCW table exists."""
        return self._repo.table_exists()

    def count_rows(self) -> int:
        """Count total rows in GPCW table."""
        return self._repo.count_rows()

    def count_stocks(self) -> int:
        """Count distinct stocks in GPCW table."""
        return self._repo.count_stocks()


def get_gpcw_service() -> GpcwApplicationService:
    """Get singleton GpcwApplicationService instance."""
    global _gpcw_service
    if _gpcw_service is None:
        _gpcw_service = GpcwApplicationService()
    return _gpcw_service


def create_gpcw_service() -> GpcwApplicationService:
    """Factory for GpcwApplicationService (used by bootstrap wiring)."""
    return GpcwApplicationService()
