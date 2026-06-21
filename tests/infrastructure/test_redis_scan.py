"""Redis SCAN helper tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.redis_client import delete_keys_by_pattern, scan_keys


def test_scan_keys_iterates_until_cursor_zero():
    client = MagicMock()
    client.scan.side_effect = [(1, ["a:1", "a:2"]), (0, ["a:3"])]
    assert scan_keys(client, "a:*") == ["a:1", "a:2", "a:3"]
    assert client.scan.call_count == 2


def test_delete_keys_by_pattern_batches_delete():
    client = MagicMock()
    client.scan.return_value = (0, ["k1", "k2"])
    client.delete.return_value = 2
    assert delete_keys_by_pattern(client, "k*") == 2
    client.delete.assert_called_once_with("k1", "k2")
