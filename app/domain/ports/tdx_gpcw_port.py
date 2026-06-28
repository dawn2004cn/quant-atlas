from __future__ import annotations

"""Port for TDX gpcw professional financial data (MySQL ``tdx_gpcw_financial``)."""

from abc import ABC, abstractmethod
from typing import Any


class TdxGpcwRepository(ABC):
    """Read-only GPCW financial data access for application services."""

    @abstractmethod
    def get_stock_periods(self, code: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_stock_data(self, code: str, report_date: int) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def get_stock_data_by_indexed_code(
        self, indexed_code: str, report_date: int
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def table_exists(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def count_rows(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_stocks(self) -> int:
        raise NotImplementedError
