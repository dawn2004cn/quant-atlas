"""Repository base classes and interfaces."""

from abc import ABC, abstractmethod
from typing import Any


class InvestmentManagerRepositoryBase(ABC):
    """投资经理Repository接口"""

    @abstractmethod
    def get_manager(self, manager_id: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def list_managers(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def upsert_manager(self, row: Any) -> None:
        pass

    @abstractmethod
    def trade_stats_by_manager(self) -> dict[str, dict[str, Any]]:
        pass

    @abstractmethod
    def activate_next_batch(self, *, batch_size: int = 10) -> list[str]:
        pass

    @abstractmethod
    def upsert_nav(self, *, manager_id: str, nav_date: str, equity: float, cash: float, total_fee: float, total_tax: float, note: str = "") -> None:
        pass

    @abstractmethod
    def get_nav_series(self, manager_id: str, *, limit: int = 420) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def append_trade(self, payload: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def list_trades(self, manager_id: str, *, limit: int = 400) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def latest_holdings_snap_date_before(self, manager_id: str, snap_date: str) -> str | None:
        pass

    @abstractmethod
    def upsert_position_state(self, *, manager_id: str, symbol: str, shares: int, avg_cost: float, entry_cost: float, high_px: float, entry_date: str) -> None:
        pass

    @abstractmethod
    def get_holdings_snap(self, manager_id: str, snap_date: str) -> list[dict[str, Any]]:
        pass


class BasicMarketDataRepositoryBase(ABC):
    """基础市场数据Repository接口"""

    @abstractmethod
    def replace_longhu_day(self, trade_date: str, rows: list[dict[str, Any]]) -> int:
        pass

    @abstractmethod
    def list_longhu_by_date(self, trade_date: str, *, limit: int = 500) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def set_meta(self, key: str, value: str) -> None:
        pass

    @abstractmethod
    def get_meta(self, key: str) -> str | None:
        pass

    @abstractmethod
    def upsert_financial_stash(self, code: str, payload: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def insert_yanbao_batch(self, category: str, items: list[dict[str, Any]], batch_id: str) -> int:
        pass

    @abstractmethod
    def upsert_longhu_rows(self, rows: list[dict[str, Any]]) -> int:
        pass

    @abstractmethod
    def count_longhu_rows(self) -> int:
        pass

    @abstractmethod
    def latest_longhu_trade_date(self) -> str | None:
        pass

    @abstractmethod
    def list_longhu_latest_dates(self, limit: int = 20) -> list[str]:
        pass

    @abstractmethod
    def list_longhu_for_code(self, code: str, *, limit: int = 20) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def list_yanbao(self, *, category: str | None = None, limit: int = 120) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def count_financial_stash_rows(self) -> int:
        pass


class NewsArchiveRepositoryBase(ABC):
    """新闻归档Repository接口"""

    @abstractmethod
    def latest_fetched_at(self, market: str, symbol: str) -> str | None:
        pass

    @abstractmethod
    def get_meta(self, market: str, symbol: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def upsert_meta(self, market: str, symbol: str, *, company_name: str, industry_hint: str) -> None:
        pass

    @abstractmethod
    def ingest_snapshot(self, market: str, symbol: str, snapshot: dict[str, Any]) -> int:
        pass

    @abstractmethod
    def list_for_symbol(self, market: str, symbol: str, *, limit: int = 80) -> list[dict[str, Any]]:
        pass


class SignalFlagPoolRepositoryBase(ABC):
    """信号旗池Repository接口"""

    @abstractmethod
    def list_dates(self, *, limit: int = 120) -> list[str]:
        pass

    @abstractmethod
    def get_pool(self, pool_date: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def replace_pool(self, pool_date: str, rows: list[dict[str, Any]]) -> int:
        pass


class MomentsRepositoryBase(ABC):
    """时刻动态Repository接口"""

    @abstractmethod
    def create_post(self, *, actor_type: str, actor_id: str, author_name: str, content_text: str, content: dict[str, Any] | None = None, market_date: str | None = None) -> int:
        pass

    @abstractmethod
    def add_attachment(self, *, post_id: int, media_type: str, file_name: str, file_path: str, file_url: str, mime_type: str | None, size_bytes: int, meta: dict[str, Any] | None = None) -> int:
        pass

    @abstractmethod
    def list_feed(self, *, limit: int = 50, before_post_id: int | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def toggle_like(self, *, post_id: int, user_id: str) -> dict[str, Any]:
        pass


class AnalysisReportRepositoryBase(ABC):
    """分析报告Repository接口"""

    @abstractmethod
    def save_report(self, ticker: str, user_id: int, dashboard: str, prediction: str, price: float) -> None:
        pass

    @abstractmethod
    def get_pending_reports(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def update_validation(self, report_id: str, score: float) -> None:
        pass
