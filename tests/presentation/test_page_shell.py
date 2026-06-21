from __future__ import annotations

from app.presentation.web.page_shell import ux_env_hints


def test_ux_env_hints_mysql_disabled() -> None:
    class _Settings:
        use_mysql = False
        tdx_root_path = "/tdx"

    hints = ux_env_hints(_Settings())  # type: ignore[arg-type]
    titles = [h["title"] for h in hints]
    assert any("MySQL" in t for t in titles)
