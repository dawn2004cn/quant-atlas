from __future__ import annotations

"""财务数据：在线 get_finance_info + 历史财务 crawler/reader。"""


from pathlib import Path
from typing import Any

from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.connection_hq import TdxHqConnection
from app.infrastructure.pytdx.exceptions import PytdxMethodNotAllowedError
from app.infrastructure.pytdx.runtime import require_pytdx
from app.infrastructure.pytdx.symbols import code6_from_symbol, market_code_from_symbol


class TdxFinanceApi(BasePytdxApi):
    module = "finance"

    def __init__(self, connection: TdxHqConnection | None = None) -> None:
        self._hq = connection or TdxHqConnection()

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        require_pytdx()
        if method == "get_finance_info":
            if len(args) >= 2:
                market, code = int(args[0]), str(args[1])
            elif kwargs.get("symbol"):
                market = market_code_from_symbol(str(kwargs["symbol"]))
                code = code6_from_symbol(str(kwargs["symbol"]))
            elif len(args) == 1:
                market = market_code_from_symbol(str(args[0]))
                code = code6_from_symbol(str(args[0]))
            else:
                raise ValueError("get_finance_info requires (market, code) or symbol=")
            return self._hq.execute("get_finance_info", market, code)
        if method == "crawl_history_financial_list":
            from pytdx.crawler.history_financial_crawler import HistoryFinancialListCrawler

            crawler = HistoryFinancialListCrawler()
            return crawler.fetch_and_parse()
        if method == "crawl_history_financial_file":
            filename = str(args[0]) if args else str(kwargs.get("filename", ""))
            dest_dir = str(args[1]) if len(args) > 1 else str(kwargs.get("dest_dir", "."))
            from pytdx.crawler.history_financial_crawler import HistoryFinancialCrawler

            crawler = HistoryFinancialCrawler()
            path = Path(dest_dir) / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            crawler.fetch_and_parse(reporthook=None, path_to_download=str(path))
            return {"path": str(path)}
        if method == "parse_history_financial":
            filepath = str(args[0]) if args else str(kwargs.get("filepath", ""))
            from pytdx.reader import HistoryFinancialReader

            return HistoryFinancialReader().get_df(filepath)
        raise PytdxMethodNotAllowedError(f"finance.{method}")
