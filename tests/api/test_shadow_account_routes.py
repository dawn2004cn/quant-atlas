"""Shadow Account SPA API contract tests."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/shadow-account/status", "GET"),
        ("/api/v1/shadow-account/analyze", "POST"),
    ],
)
def test_shadow_account_paths_require_login(client, path: str, method: str):
    resp = client.open(path, method=method)
    assert resp.status_code == 401
