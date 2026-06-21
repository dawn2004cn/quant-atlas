from __future__ import annotations
"""策略目录（与平台 StrategyFactory 对齐）。"""


from ...core.factory import StrategyFactory


def strategy_catalog_text() -> str:
    ids = sorted(StrategyFactory.get_registered_ids())
    return ", ".join(ids) if ids else "(无已注册策略)"
