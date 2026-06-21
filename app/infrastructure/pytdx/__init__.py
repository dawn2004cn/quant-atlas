"""Pytdx 封装：标准/扩展行情、本地读取、财务、交易、连接池。"""

from app.infrastructure.pytdx.connection_hq import TdxHqConnection
from app.infrastructure.pytdx.facade import PytdxFacade, get_pytdx_facade
from app.infrastructure.pytdx.runtime import pytdx_available, require_pytdx

# 兼容旧代码：TdxConnectionManager 指向标准行情连接
TdxConnectionManager = TdxHqConnection

__all__ = [
    "PytdxFacade",
    "TdxConnectionManager",
    "TdxHqConnection",
    "get_pytdx_facade",
    "pytdx_available",
    "require_pytdx",
]
