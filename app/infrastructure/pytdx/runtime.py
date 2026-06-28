from __future__ import annotations

"""Pytdx 运行时检测与懒加载。"""


from functools import lru_cache
from typing import Any

from app.infrastructure.pytdx.exceptions import PytdxNotAvailableError


@lru_cache(maxsize=1)
def pytdx_available() -> bool:
    try:
        import pytdx

        return True
    except ImportError:
        return False


def require_pytdx() -> None:
    if not pytdx_available():
        raise PytdxNotAvailableError(
            "pytdx is not installed. Run: pip install pytdx"
        )


def import_hq_api() -> Any:
    require_pytdx()
    from pytdx.hq import TdxHq_API

    return TdxHq_API


def import_exhq_api() -> Any:
    require_pytdx()
    from pytdx.exhq import TdxExHq_API

    return TdxExHq_API


def import_trade_api() -> Any:
    require_pytdx()
    from pytdx.trade.trade import TdxTradeApi

    return TdxTradeApi
