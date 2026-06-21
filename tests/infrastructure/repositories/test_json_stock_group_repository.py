"""JsonStockGroupRepository legacy format compatibility."""

from __future__ import annotations

import json
from pathlib import Path

from app.infrastructure.repositories.common.json_repositories import JsonStockGroupRepository


def _legacy_payload() -> dict:
    return {
        "1": {
            "groups": [
                {
                    "id": 1,
                    "name": "自选股",
                    "description": "默认分组",
                    "is_default": 1,
                }
            ],
            "items": {"1": ["600519", "000001"]},
        }
    }


def test_list_groups_reads_legacy_groups_items_shape(tmp_path: Path) -> None:
    path = tmp_path / "stock_groups.json"
    path.write_text(json.dumps(_legacy_payload()), encoding="utf-8")
    repo = JsonStockGroupRepository(path)

    groups = repo.list_groups(user_id=1)

    assert len(groups) == 1
    assert groups[0]["id"] == 1
    assert groups[0]["name"] == "自选股"
    assert "symbols" not in groups[0]


def test_list_group_symbols_reads_legacy_items_map(tmp_path: Path) -> None:
    path = tmp_path / "stock_groups.json"
    path.write_text(json.dumps(_legacy_payload()), encoding="utf-8")
    repo = JsonStockGroupRepository(path)

    symbols = repo.list_group_symbols(group_id=1, user_id=1)

    assert symbols == ["600519", "000001"]


def test_list_groups_migrates_legacy_entry_to_canonical_list(tmp_path: Path) -> None:
    path = tmp_path / "stock_groups.json"
    path.write_text(json.dumps(_legacy_payload()), encoding="utf-8")
    repo = JsonStockGroupRepository(path)

    repo.list_groups(user_id=1)
    stored = json.loads(path.read_text(encoding="utf-8"))

    assert isinstance(stored["1"], list)
    assert stored["1"][0]["symbols"] == ["600519", "000001"]
