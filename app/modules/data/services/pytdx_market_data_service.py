from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""基于 Pytdx 的行情/财务拉取（供业务层直接调用）。"""





from typing import Any



from app.modules.system.services.helpers.pytdx_access import get_pytdx_market_port

from app.core.logger import get_logger

from app.domain.shared.pytdx_symbols import code6_from_symbol, market_code_from_symbol



logger = get_logger(__name__)



# pytdx K线 category：9=日K

KLINE_CATEGORY_DAY = 9





class PytdxMarketDataService:

    """封装常用 Pytdx 读数，失败时记录日志并返回空结构。"""



    def is_available(self) -> bool:

        return get_pytdx_market_port().is_available()



    def connection_status(self) -> GenericResponseDTO:

        if not self.is_available():

            return {"available": False}

        try:

            return get_pytdx_market_port().status()

        except Exception as exc:

            logger.warning("pytdx status failed: %s", exc)

            return {"available": True, "error": str(exc)}



    def get_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:

        if not symbols or not self.is_available():

            return []

        try:

            return get_pytdx_market_port().get_security_quotes_for_symbols(symbols)

        except Exception as exc:

            logger.warning("pytdx get_quotes failed: %s", exc)

            return []



    def get_daily_bars(

        self,

        symbol: str,

        *,

        count: int = 120,

        category: int = KLINE_CATEGORY_DAY,

    ) -> list[dict[str, Any]]:

        if not self.is_available():

            return []

        market = market_code_from_symbol(symbol)

        code = code6_from_symbol(symbol)

        try:

            raw = get_pytdx_market_port().invoke(

                "hq",

                "get_security_bars",

                category,

                market,

                code,

                0,

                count,

            )

            return raw if isinstance(raw, list) else []

        except Exception as exc:

            logger.warning("pytdx get_daily_bars %s failed: %s", symbol, exc)

            return []



    def get_finance_info(self, symbol: str) -> GenericResponseDTO | None:

        if not self.is_available():

            return None

        try:

            data = get_pytdx_market_port().finance_call("get_finance_info", symbol=symbol)

            return data if isinstance(data, dict) else None

        except Exception as exc:

            logger.warning("pytdx get_finance_info %s failed: %s", symbol, exc)

            return None



    def get_xdxr_info(self, symbol: str) -> list[dict[str, Any]]:

        if not self.is_available():

            return []

        market = market_code_from_symbol(symbol)

        code = code6_from_symbol(symbol)

        try:

            raw = get_pytdx_market_port().invoke("hq", "get_xdxr_info", market, code)

            return raw if isinstance(raw, list) else []

        except Exception as exc:

            logger.warning("pytdx get_xdxr_info %s failed: %s", symbol, exc)

            return []



    def read_local_daily(self, symbol: str) -> list[dict[str, Any]]:

        """本机通达信 vipdoc 日 K（需 TDX_ROOT_PATH）。"""

        if not self.is_available():

            return []

        try:

            df = get_pytdx_market_port().invoke(

                "reader",

                "read_daily",

                kwargs={"symbol": symbol},

            )

            if isinstance(df, list):

                return df

            return []

        except Exception as exc:

            logger.warning("pytdx read_local_daily %s failed: %s", symbol, exc)

            return []





_pytdx_market_data_service: PytdxMarketDataService | None = None





def get_pytdx_market_data_service() -> PytdxMarketDataService:

    global _pytdx_market_data_service

    if _pytdx_market_data_service is None:

        _pytdx_market_data_service = PytdxMarketDataService()

    return _pytdx_market_data_service

