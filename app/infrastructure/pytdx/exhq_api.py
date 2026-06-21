from __future__ import annotations
"""扩展行情 API（pytdx.exhq）。"""


from typing import Any

from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.connection_exhq import TdxExHqConnection


class TdxExHqApi(BasePytdxApi):
    module = "exhq"

    def __init__(self, connection: TdxExHqConnection | None = None) -> None:
        self._conn = connection or TdxExHqConnection()

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return self._conn.execute(method, *args, **kwargs)

    def status(self) -> dict[str, Any]:
        return self._conn.status()
