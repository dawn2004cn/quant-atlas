from __future__ import annotations

"""标准行情 API（pytdx.hq）。"""


from typing import Any

from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.connection_hq import TdxHqConnection
from app.infrastructure.pytdx.symbols import quote_tuple_from_symbol


class TdxHqApi(BasePytdxApi):
    module = "hq"

    def __init__(self, connection: TdxHqConnection | None = None) -> None:
        self._conn = connection or TdxHqConnection()

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return self._conn.execute(method, *args, **kwargs)

    _MAX_QUOTES_PER_CALL = 80

    def get_security_quotes_for_symbols(self, symbols: list[str]) -> list[dict[str, Any]]:
        """便捷：按项目 symbol 列表拉实时行情（每批最多 80 只，pytdx 协议限制）。"""
        stocks = [quote_tuple_from_symbol(s) for s in symbols if s]
        if not stocks:
            return []
        out: list[dict[str, Any]] = []
        step = self._MAX_QUOTES_PER_CALL
        for i in range(0, len(stocks), step):
            batch = stocks[i : i + step]
            part = self._dispatch("get_security_quotes", batch) or []
            if isinstance(part, list):
                out.extend(part)
        return out

    def status(self) -> dict[str, Any]:
        return self._conn.status()
