from __future__ import annotations

"""MySQL 连接参数（与 SQLite 二选一，由 ``DATABASE_BACKEND=mysql`` 启用）。"""


from dataclasses import dataclass


@dataclass(frozen=True)
class MysqlSettings:
    host: str
    port: int
    user: str
    password: str
    database: str

    def describe(self) -> str:
        return f"mysql://{self.user}@{self.host}:{self.port}/{self.database}"
