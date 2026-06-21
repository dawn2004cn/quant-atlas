from __future__ import annotations
"""兼容入口：RD-Agent 因子循环实现位于 ``infrastructure.rdagent.rdagent_factor_loop``。"""


from app.infrastructure.rdagent.rdagent_factor_loop import (
    prepare_patched_factor_template,
    run_factor_mining_loop,
)

__all__ = ["prepare_patched_factor_template", "run_factor_mining_loop"]
