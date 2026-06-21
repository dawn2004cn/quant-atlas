"""RD-Agent 提交前校验（无 rdagent 包、无网络）。"""

from __future__ import annotations

import pytest

from app.domain.exceptions import InvalidConfigurationError
from app.infrastructure.rdagent.submission_validate import validate_rd_factor_submission


def test_validate_rejects_missing_provider_dir(tmp_path) -> None:
    body: dict = {}
    with pytest.raises(InvalidConfigurationError, match="路径不存在"):
        validate_rd_factor_submission(body, base_dir=tmp_path)


def test_validate_rejects_default_bin_not_ready(tmp_path) -> None:
    bin_dir = tmp_path / "instance" / "qlib_bin"
    bin_dir.mkdir(parents=True)
    body: dict = {}
    with pytest.raises(InvalidConfigurationError, match="未就绪"):
        validate_rd_factor_submission(body, base_dir=tmp_path)


def test_validate_accepts_default_bin_with_calendar(tmp_path) -> None:
    cal = tmp_path / "instance" / "qlib_bin" / "calendars" / "day.txt"
    cal.parent.mkdir(parents=True)
    cal.write_text("2020-01-02\n2020-01-03\n", encoding="utf-8")
    validate_rd_factor_submission({}, base_dir=tmp_path)


def test_validate_custom_uri_dir_without_calendar_ok(tmp_path) -> None:
    custom = tmp_path / "my_qlib_data"
    custom.mkdir()
    (custom / "placeholder.txt").write_text("x", encoding="utf-8")
    validate_rd_factor_submission({"provider_uri": str(custom)}, base_dir=tmp_path)

