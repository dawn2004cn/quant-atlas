"""通达信连接管理器（兼容层，实现已迁至 pytdx.connection_hq）。"""

from app.infrastructure.pytdx import TdxConnectionManager, TdxHqConnection

__all__ = ["TdxConnectionManager", "TdxHqConnection"]
