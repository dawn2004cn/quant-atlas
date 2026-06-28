from __future__ import annotations

"""QuestDB / ClickHouse connection settings (from environment)."""

from dataclasses import dataclass

from app.core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int


@dataclass(frozen=True)
class QuestDBSettings:
    host: str
    http_port: int
    pg_port: int
    ilp_port: int
    user: str
    password: str
    database: str

    @property
    def http_base_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    def describe(self) -> str:
        return (
            f"questdb://{self.user}@{self.host} "
            f"(pg:{self.pg_port}, http:{self.http_port}, ilp:{self.ilp_port})"
        )


@dataclass(frozen=True)
class ClickHouseSettings:
    host: str
    port: int
    user: str
    password: str
    database: str

    @property
    def http_base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def describe(self) -> str:
        return f"clickhouse://{self.user}@{self.host}:{self.port}/{self.database}"


def load_questdb_settings() -> QuestDBSettings | None:
    if not get_runtime_bool("ENABLE_QUESTDB", True):
        return None
    host = (get_runtime("QUESTDB_HOST", "") or "").strip()
    if not host:
        return None
    return QuestDBSettings(
        host=host,
        http_port=get_runtime_int("QUESTDB_HTTP_PORT", 8812),
        pg_port=get_runtime_int("QUESTDB_PG_PORT", get_runtime_int("QUESTDB_PORT", 8813)),
        ilp_port=get_runtime_int("QUESTDB_ILP_PORT", 9009),
        user=(get_runtime("QUESTDB_USER", "admin") or "admin").strip(),
        password=get_runtime("QUESTDB_PASSWORD", "") or "",
        database=(get_runtime("QUESTDB_DATABASE", "qdb") or "qdb").strip(),
    )


def load_clickhouse_settings() -> ClickHouseSettings | None:
    if not get_runtime_bool("ENABLE_CLICKHOUSE", True):
        return None
    host = (get_runtime("CLICKHOUSE_HOST", "") or "").strip()
    if not host:
        return None
    return ClickHouseSettings(
        host=host,
        port=get_runtime_int("CLICKHOUSE_PORT", 8123),
        user=(get_runtime("CLICKHOUSE_USER", "default") or "default").strip(),
        password=get_runtime("CLICKHOUSE_PASSWORD", "") or "",
        database=(get_runtime("CLICKHOUSE_DATABASE", "default") or "default").strip(),
    )
