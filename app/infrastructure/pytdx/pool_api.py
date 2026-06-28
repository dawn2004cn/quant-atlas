from __future__ import annotations

"""连接池（pytdx.pool.TdxHqPool_API）。"""


from typing import Any

from app.infrastructure.external.tdx_selector import TdxBestServersConnect
from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.catalog import allowed_methods
from app.infrastructure.pytdx.exceptions import PytdxMethodNotAllowedError
from app.infrastructure.pytdx.runtime import import_hq_api, require_pytdx
from app.infrastructure.pytdx.serialize import to_jsonable


class TdxHqPoolApi(BasePytdxApi):
    module = "pool"

    def __init__(self) -> None:
        self._pool: Any | None = None
        self._servers: list[tuple[str, int]] = []

    def init_pool(self, servers: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        require_pytdx()
        from pytdx.pool.hqpool import TdxHqPool_API
        from pytdx.pool.ippool import RandomIPPool

        if servers:
            ips = [(str(s["ip"]), int(s["port"])) for s in servers]
        else:
            best = TdxBestServersConnect().get_best_tdx_servers()
            ips = [(s["ip"], int(s["port"])) for s in (best or [])]
        self._servers = ips
        if not ips:
            raise RuntimeError("no TDX servers for pool")
        hq_cls = import_hq_api()
        ippool = RandomIPPool(hq_cls, ips)
        ippool.setup()
        self._pool = TdxHqPool_API(hq_cls, ippool)
        return self.pool_status()

    def pool_status(self) -> dict[str, Any]:
        return {
            "initialized": self._pool is not None,
            "servers": [{"ip": ip, "port": port} for ip, port in self._servers],
        }

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        name = (method or "").strip()
        if name == "init_pool":
            return self.init_pool(list(args[0]) if args else None)
        if name == "pool_status":
            return self.pool_status()
        if name not in allowed_methods("hq"):
            raise PytdxMethodNotAllowedError(f"pool.{name} not allowed")
        if self._pool is None:
            self.init_pool()
        raw = getattr(self._pool, name)(*args, **kwargs)
        return to_jsonable(raw)

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        return self.call(method, *args, **kwargs)
