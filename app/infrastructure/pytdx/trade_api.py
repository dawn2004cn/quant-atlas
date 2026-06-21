from __future__ import annotations
"""交易 API（pytdx.trade，需本机 TdxTradeServer）。"""


from typing import Any

from app.config import get_settings
from app.core.runtime_config import get_runtime
from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.runtime import import_trade_api


class TdxTradeApiWrapper(BasePytdxApi):
    module = "trade"

    def __init__(self, *, endpoint: str | None = None) -> None:
        settings = get_settings()
        self._endpoint = (
            endpoint
            or get_runtime("TDX_TRADE_ENDPOINT", "")
            or "http://127.0.0.1:10092/api"
        ).strip()
        self._client = None

    def _client_lazy(self) -> Any:
        if self._client is None:
            TradeCls = import_trade_api()
            self._client = TradeCls(endpoint=self._endpoint)
        return self._client

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        client = self._client_lazy()
        if method == "call":
            func = args[0] if args else kwargs.get("func")
            params = args[1] if len(args) > 1 else kwargs.get("params")
            return client.call(func, params)
        func = getattr(client, method, None)
        if not callable(func):
            raise AttributeError(f"unknown trade method: {method}")
        return func(*args, **kwargs)

    def status(self) -> dict[str, Any]:
        out: dict[str, Any] = {"module": "trade", "endpoint": self._endpoint}
        try:
            out["ping"] = self._dispatch("ping")
            out["reachable"] = True
        except Exception as exc:
            out["reachable"] = False
            out["error"] = str(exc)
        return out
