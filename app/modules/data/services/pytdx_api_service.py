from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Pytdx 应用服务：供 API 与其它模块统一调用。"""





from typing import Any



from app.modules.data.services.pytdx_market_data_service import get_pytdx_market_data_service

from app.modules.system.services.helpers.pytdx_access import get_pytdx_market_port





class PytdxApiService:

    def catalog(self) -> GenericResponseDTO[str, list[dict[str, object]]]:

        get_pytdx_market_port().require_available()

        return get_pytdx_market_port().catalog()



    def status(self) -> GenericResponseDTO:

        port = get_pytdx_market_port()

        try:

            port.require_available()

        except Exception as exc:

            return {"pytdx_installed": False, "error": str(exc)}

        return port.status()



    def invoke(

        self,

        module: str,

        method: str,

        args: list[Any] | None = None,

        kwargs: dict[str, Any] | None = None,

    ) -> Any:

        get_pytdx_market_port().require_available()

        mod = (module or "").strip().lower()

        if mod not in ("hq", "exhq", "reader", "finance", "trade", "pool"):

            raise ValueError("module must be hq|exhq|reader|finance|trade|pool")

        return get_pytdx_market_port().invoke(

            mod,

            method,

            *(args or []),

            **(kwargs or {}),

        )



    def hq_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:

        get_pytdx_market_port().require_available()

        return get_pytdx_market_port().get_security_quotes_for_symbols(symbols)



    def market_snapshot(self, symbols: list[str]) -> GenericResponseDTO:

        """常用数据打包：连接状态 + 实时行情 + 首标的日K/财务。"""

        mds = get_pytdx_market_data_service()

        out: dict[str, Any] = {

            "status": mds.connection_status(),

            "quotes": mds.get_quotes(symbols),

        }

        if symbols:

            sym = symbols[0]

            out["sample"] = {

                "symbol": sym,

                "daily_bars": mds.get_daily_bars(sym, count=10),

                "finance": mds.get_finance_info(sym),

            }

        return out

