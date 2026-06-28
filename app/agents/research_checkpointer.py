from __future__ import annotations

"""LangGraph checkpointer factory: in-memory default, optional Postgres."""


import os
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from ..core.logger import get_logger
from ..core.runtime_config import get_runtime

logger = get_logger(__name__)

@dataclass
class CheckpointerHandle:
    """持有 checkpointer 与可选的 Postgres 上下文，便于应用关闭时释放。"""

    saver: BaseCheckpointSaver
    _cm: AbstractContextManager[Any] | None = field(default=None, repr=False)

    def close(self) -> None:
        if self._cm is not None:
            try:
                self._cm.__exit__(None, None, None)
            except Exception as exc:
                logger.warning("checkpointer context exit: %s", exc)
            finally:
                self._cm = None


def create_checkpointer_handle_from_env() -> CheckpointerHandle:
    """
    环境变量：
    - ``LANGGRAPH_CHECKPOINTER``：`memory`（默认）或 `postgres`
    - ``LANGGRAPH_POSTGRES_URI``：优先；否则可读 ``DATABASE_URL``（须为 libpq 连接串）

    首次使用 Postgres 时会调用 ``.setup()`` 建表。
    """
    mode = get_runtime("LANGGRAPH_CHECKPOINTER", "memory").strip().lower()
    uri = (os.getenv("LANGGRAPH_POSTGRES_URI") or os.getenv("DATABASE_URL") or "").strip()

    if mode == "postgres" and uri:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except Exception as exc:
            logger.warning("无法加载 PostgresSaver（将使用 MemorySaver）: %s", exc)
            return CheckpointerHandle(saver=MemorySaver(), _cm=None)

        try:
            cm = PostgresSaver.from_conn_string(uri)
            saver: BaseCheckpointSaver = cm.__enter__()
            saver.setup()
            logger.info("LangGraph Postgres checkpointer 已初始化并完成 setup()")
            return CheckpointerHandle(saver=saver, _cm=cm)
        except Exception as exc:
            logger.exception("Postgres checkpointer 初始化失败，回退 MemorySaver: %s", exc)
            return CheckpointerHandle(saver=MemorySaver(), _cm=None)

    return CheckpointerHandle(saver=MemorySaver(), _cm=None)
