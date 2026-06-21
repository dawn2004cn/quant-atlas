"""Manual JQKA integration checks — skipped in automated pytest runs."""

from __future__ import annotations

import pytest

pytest.skip("Manual JQKA integration test", allow_module_level=True)
