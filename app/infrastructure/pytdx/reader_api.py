from __future__ import annotations

"""本地通达信数据文件读取（pytdx.reader）。"""


from pathlib import Path
from typing import Any

from app.config import get_settings
from app.infrastructure.pytdx.api_base import BasePytdxApi
from app.infrastructure.pytdx.exceptions import PytdxMethodNotAllowedError
from app.infrastructure.pytdx.runtime import require_pytdx
from app.infrastructure.pytdx.symbols import code6_from_symbol, market_code_from_symbol
from app.infrastructure.tdx_local.paths import resolve_tdx_root


class TdxReaderApi(BasePytdxApi):
    module = "reader"

    def __init__(self, *, tdx_root: str | None = None) -> None:
        settings = get_settings()
        self._root = resolve_tdx_root(tdx_root or settings.tdx_root_path)

    def _vipdoc_market(self, symbol: str) -> str:
        m = market_code_from_symbol(symbol)
        return "sh" if m == 1 else "sz"

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        require_pytdx()
        if not self._root:
            raise FileNotFoundError("TDX_ROOT_PATH not configured")

        if method == "read_daily":
            symbol = str(args[0]) if args else kwargs.get("symbol", "")
            market = kwargs.get("market") or self._vipdoc_market(symbol)
            return self._read_daily(market, code6_from_symbol(symbol))
        if method == "read_minute":
            symbol = str(args[0]) if args else kwargs.get("symbol", "")
            market = kwargs.get("market") or self._vipdoc_market(symbol)
            return self._read_minute(market, code6_from_symbol(symbol))
        if method == "read_lc_minute":
            symbol = str(args[0]) if args else kwargs.get("symbol", "")
            market = kwargs.get("market") or self._vipdoc_market(symbol)
            return self._read_lc_minute(market, code6_from_symbol(symbol))
        if method == "read_exhq_daily":
            market, code = args[0], args[1]
            return self._read_exhq_daily(str(market), str(code))
        if method == "read_gbbq":
            return self._read_gbbq()
        if method == "read_block":
            block_file = str(args[0]) if args else kwargs.get("block_file", "")
            return self._read_block(block_file)
        if method == "read_customer_block":
            block_file = str(args[0]) if args else kwargs.get("block_file", "")
            return self._read_customer_block(block_file)
        if method == "read_history_financial":
            filepath = str(args[0]) if args else kwargs.get("filepath", "")
            return self._read_history_financial(filepath)
        raise PytdxMethodNotAllowedError(f"reader.{method}")

    def _read_daily(self, market: str, code6: str) -> Any:
        from pytdx.reader import TdxDailyBarReader

        reader = TdxDailyBarReader()
        reader.vipdoc_path = str(Path(self._root) / "vipdoc")
        return reader.get_df(f"{market}{code6}")

    def _read_minute(self, market: str, code6: str) -> Any:
        from pytdx.reader import TdxMinBarReader

        reader = TdxMinBarReader()
        reader.vipdoc_path = str(Path(self._root) / "vipdoc")
        return reader.get_df(f"{market}{code6}")

    def _read_lc_minute(self, market: str, code6: str) -> Any:
        from pytdx.reader import TdxLCMinBarReader

        reader = TdxLCMinBarReader()
        reader.vipdoc_path = str(Path(self._root) / "vipdoc")
        return reader.get_df(f"{market}{code6}")

    def _read_exhq_daily(self, market: str, code: str) -> Any:
        from pytdx.reader import TdxExHqDailyBarReader

        reader = TdxExHqDailyBarReader()
        return reader.get_df(f"{market}{code}")

    def _read_gbbq(self) -> Any:
        from pytdx.reader import GbbqReader

        path = Path(self._root) / "T0002" / "hq_cache" / "gbbq"
        return GbbqReader().get_df(str(path))

    def _read_block(self, block_file: str) -> Any:
        from pytdx.reader import BlockReader

        path = Path(self._root) / "T0002" / "hq_cache" / block_file
        return BlockReader().get_df(str(path))

    def _read_customer_block(self, block_file: str) -> Any:
        from pytdx.reader import CustomerBlockReader

        path = Path(self._root) / "T0002" / "hq_cache" / block_file
        return CustomerBlockReader().get_df(str(path))

    def _read_history_financial(self, filepath: str) -> Any:
        from pytdx.reader import HistoryFinancialReader

        return HistoryFinancialReader().get_df(filepath)

    def status(self) -> dict[str, Any]:
        return {
            "module": "reader",
            "tdx_root": self._root,
            "configured": bool(self._root),
        }
