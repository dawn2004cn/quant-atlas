"""Manual Xueqiu integration checks — skipped in automated pytest runs."""

from __future__ import annotations

import pytest

pytest.skip(
    "Manual Xueqiu integration test; run as script only",
    allow_module_level=True,
)
