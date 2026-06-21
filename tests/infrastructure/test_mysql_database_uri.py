from __future__ import annotations

from app.infrastructure.database.mysql_settings import MysqlSettings
from app.infrastructure.database.orm import mysql_database_uri


def test_mysql_database_uri_builds_non_empty_sqlalchemy_uri() -> None:
    ms = MysqlSettings(
        host="192.168.8.103",
        port=3307,
        user="quant_atlas",
        password="secret",
        database="quant_atlas",
    )

    uri = mysql_database_uri(ms)

    assert uri.startswith("mysql+pymysql://")
    assert "192.168.8.103:3307/quant_atlas" in uri
    assert uri.strip() != ""
