"""MySQL history reload table suffix / swap SQL."""

from __future__ import annotations

import pytest

from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import (
    _table_for_code,
    _validate_table_suffix,
)


def test_table_for_code_new_suffix() -> None:
    assert _table_for_code("sh600519", suffix="_new") == "stock_history_sh_new"


def test_validate_suffix_rejects_bad() -> None:
    with pytest.raises(ValueError):
        _validate_table_suffix(";drop")
