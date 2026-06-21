from __future__ import annotations
"""PostgreSQL / TimescaleDB connection settings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PostgresSettings:
    host: str
    port: int
    user: str
    password: str
    database: str

    def describe(self) -> str:
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"
