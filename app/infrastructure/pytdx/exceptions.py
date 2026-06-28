from __future__ import annotations

"""Pytdx 封装层异常。"""



class PytdxNotAvailableError(RuntimeError):
    """未安装 pytdx 或导入失败。"""


class PytdxConnectionError(ConnectionError):
    """无法连接行情/扩展行情服务器。"""


class PytdxMethodNotAllowedError(ValueError):
    """方法不在白名单内（防止任意反射调用）。"""
