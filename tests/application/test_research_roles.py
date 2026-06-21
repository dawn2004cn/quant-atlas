"""研究员 / 交易员角色与 Qlib、RD 写权限。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.user.services.user.user_service import UserApplicationService
from app.presentation.web.models import SessionUser


@pytest.mark.parametrize(
    "role,expect",
    [
        ("viewer", False),
        ("trader", False),
        ("researcher", True),
        ("developer", True),
        ("admin", True),
    ],
)
def test_can_run_research_writes(role: str, expect: bool) -> None:
    u = SessionUser(1, "t", role)
    assert u.can_run_research_writes() is expect


@pytest.mark.parametrize(
    "role,expect",
    [
        ("viewer", False),
        ("trader", False),
        ("researcher", True),
        ("developer", True),
        ("admin", True),
    ],
)
def test_may_trigger_server_data_ingestion(role: str, expect: bool) -> None:
    u = SessionUser(1, "t", role)
    assert u.may_trigger_server_data_ingestion() is expect


@pytest.mark.parametrize(
    "role,expect",
    [
        ("viewer", False),
        ("trader", False),
        ("researcher", True),
        ("developer", True),
        ("admin", True),
    ],
)
def test_may_run_expensive_ai_pipeline(role: str, expect: bool) -> None:
    u = SessionUser(1, "t", role)
    assert u.may_run_expensive_ai_pipeline() is expect


def test_user_service_accepts_new_roles() -> None:
    repo = MagicMock()
    repo.create_user.return_value = True
    svc = UserApplicationService(repo)
    ok, _msg = svc.create_user("user1", "secret12", "researcher")
    assert ok
    repo.create_user.assert_called_once()
    ok2, msg2 = svc.create_user("u2", "short", "researcher")
    assert not ok2
    assert msg2  # Should contain validation error about username/password length
