from __future__ import annotations
"""Global Stock Metadata Accessor — delegates to ``StockMetadataRepository`` Port."""


from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.ports.stock_metadata_port import StockMetadataRepository

logger = get_logger(__name__)

_default_repo: StockMetadataRepository | None = None


def bind_stock_metadata_repository(repository: StockMetadataRepository) -> None:
    """Called from bootstrap to inject the infrastructure implementation."""
    global _default_repo
    _default_repo = repository


def _repository() -> StockMetadataRepository:
    if _default_repo is None:
        raise RuntimeError(
            "StockMetadataRepository not configured; bootstrap must call bind_stock_metadata_repository()"
        )
    return _default_repo


class StockMetadataProvider:
    """Provides fundamental stock data from reference table via Port."""

    @staticmethod
    def get_basic_info(code: str) -> GenericResponseDTO[str, object]:
        try:
            return _repository().get_basic_info(code)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Metadata lookup failed for %s: %s", code, exc)
            return {}


def enrich_stock_list(stocks: list[dict]) -> list[dict]:
    if not stocks:
        return stocks
    try:
        return _repository().enrich_stock_list(stocks)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Batch enrich failed: %s", exc)
        return stocks


def get_stock_metadata_batch(codes: list[str]) -> GenericResponseDTO[str, dict]:
    if not codes:
        return {}
    try:
        return _repository().get_batch(codes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_stock_metadata_batch failed: %s", exc)
        return {}
