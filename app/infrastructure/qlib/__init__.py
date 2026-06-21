"""
Qlib 集成包（阶段 1：适配器与导出，不顶层 import pyqlib）。

- 勿在本包顶层 import pyqlib，避免未安装 Qlib 时拖垮整个应用。
- 开关见环境变量 ENABLE_QLIB 与 docs/roadmap_qlib_rd_agent.md。
"""

from .data_adapter import QlibDataAdapter
from .symbol_map import cn_to_qlib_instrument, to_qlib_instrument

__all__ = ["QlibDataAdapter", "cn_to_qlib_instrument", "to_qlib_instrument"]
