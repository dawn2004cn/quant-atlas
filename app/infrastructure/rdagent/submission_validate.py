from __future__ import annotations

"""RD-Agent 因子任务提交前校验：数据目录存在、平台默认 ``qlib_bin`` 就绪或可行动指引。"""


from pathlib import Path
from typing import Any

from ...config import BASE_DIR
from ...core.runtime_config import get_runtime_bool
from ...domain.exceptions import InvalidConfigurationError
from ...domain.services.rdagent_config import parse_rdagent_loop_params

# 与 ``run_factor_mining_loop`` 默认 provider 对齐
_MIN_CSV_FOR_DUMP_HINT = 1


def _qlib_bin_ready_at(data_dir: Path) -> bool:
    cal = data_dir / "calendars" / "day.txt"
    try:
        return cal.is_file() and cal.stat().st_size > 0
    except OSError:
        return False


def _csv_count_qlib_export(root: Path) -> int:
    d = root / "instance" / "qlib_export"
    if not d.is_dir():
        return 0
    return len(list(d.glob("*.csv")))


def validate_rd_factor_submission(body: dict[str, Any], *, base_dir: Path | None = None) -> None:
    """
    在创建 job 之前调用；不通过时抛出 ``InvalidConfigurationError``（含 ``details`` 供前端展示）。

    - 自定义 ``provider_uri``：须为已存在的目录。
    - 平台默认 ``instance/qlib_bin``：须存在非空 ``calendars/day.txt``（与管线 ``qlib_bin_ready`` 判定一致），
      否则若 ``ENABLE_QLIB=1`` 且已有 CSV，则在 details 中提示先 ``dump_bin``。
    """
    root = Path(base_dir or BASE_DIR).resolve()
    loop_params = parse_rdagent_loop_params(body)
    raw_uri = loop_params.get("provider_uri")
    default_bin = (root / "instance" / "qlib_bin").resolve()
    provider = str(raw_uri or default_bin).strip()
    path = Path(provider).expanduser().resolve()

    if not path.exists():
        raise InvalidConfigurationError(
            config_key="data_scope.provider_uri",
            reason=f"RD-Agent provider_uri 路径不存在: {path}"
        )
    if not path.is_dir():
        raise InvalidConfigurationError(
            config_key="data_scope.provider_uri",
            reason=f"RD-Agent provider_uri 不是目录: {path}"
        )

    get_runtime_bool("ENABLE_QLIB", False)
    bin_ready = _qlib_bin_ready_at(path)
    _csv_count_qlib_export(root)
    is_default_uri = path == default_bin

    if is_default_uri and not bin_ready:
        raise InvalidConfigurationError(
            config_key="data_scope.provider_uri",
            reason="Qlib 数据目录未就绪，无法提交 RD-Agent 因子实验"
        )

