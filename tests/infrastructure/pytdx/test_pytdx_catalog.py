"""Pytdx 目录与白名单（无需联网）。"""

from __future__ import annotations

import pytest

from app.infrastructure.pytdx.catalog import PYTDX_CATALOG, allowed_methods, catalog_to_dict
from app.infrastructure.pytdx.exceptions import PytdxMethodNotAllowedError
from app.infrastructure.pytdx.hq_api import TdxHqApi


def test_catalog_has_all_modules():
    assert set(PYTDX_CATALOG.keys()) == {"hq", "exhq", "reader", "finance", "trade", "pool"}
    doc = catalog_to_dict()
    assert "get_security_bars" in allowed_methods("hq")
    assert doc["hq"][0]["name"]


def test_hq_rejects_unknown_method():
    api = TdxHqApi.__new__(TdxHqApi)
    with pytest.raises(PytdxMethodNotAllowedError):
        api.call("evil_method")
