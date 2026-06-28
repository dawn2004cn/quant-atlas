from __future__ import annotations

"""Pytdx 统一门面。"""


from functools import lru_cache
from typing import Any

from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.catalog import PytdxModule, catalog_to_dict
from app.infrastructure.pytdx.exhq_api import TdxExHqApi
from app.infrastructure.pytdx.finance_api import TdxFinanceApi
from app.infrastructure.pytdx.hq_api import TdxHqApi
from app.infrastructure.pytdx.pool_api import TdxHqPoolApi
from app.infrastructure.pytdx.reader_api import TdxReaderApi
from app.infrastructure.pytdx.runtime import pytdx_available
from app.infrastructure.pytdx.trade_api import TdxTradeApiWrapper


class PytdxFacade:
    """系统内访问 pytdx 的推荐入口。"""

    def __init__(self) -> None:
        self._hq = TdxHqApi()
        self._exhq = TdxExHqApi()
        self._reader = TdxReaderApi()
        self._finance = TdxFinanceApi()
        self._trade = TdxTradeApiWrapper()
        self._pool = TdxHqPoolApi()

    @property
    def hq(self) -> TdxHqApi:
        return self._hq

    @property
    def exhq(self) -> TdxExHqApi:
        return self._exhq

    @property
    def reader(self) -> TdxReaderApi:
        return self._reader

    @property
    def finance(self) -> TdxFinanceApi:
        return self._finance

    @property
    def trade(self) -> TdxTradeApiWrapper:
        return self._trade

    @property
    def pool(self) -> TdxHqPoolApi:
        return self._pool

    def module(self, name: PytdxModule) -> BasePytdxApi:
        return {
            "hq": self._hq,
            "exhq": self._exhq,
            "reader": self._reader,
            "finance": self._finance,
            "trade": self._trade,
            "pool": self._pool,
        }[name]

    def invoke(self, module: PytdxModule, method: str, *args: Any, **kwargs: Any) -> Any:
        return self.module(module).call(method, *args, **kwargs)

    def status(self) -> dict[str, Any]:
        return {
            "pytdx_installed": pytdx_available(),
            "hq": self._hq.status(),
            "exhq": self._exhq.status(),
            "reader": self._reader.status(),
            "trade": self._trade.status(),
            "pool": self._pool.pool_status(),
        }

    def catalog(self) -> dict[str, list[dict[str, object]]]:
        return catalog_to_dict()


@lru_cache(maxsize=1)
def get_pytdx_facade() -> PytdxFacade:
    return PytdxFacade()
