"""Base utilities for AgentLoop.

This module contains utility functions used across the AgentLoop components.
"""

import json
from typing import Any


def estimate_tokens(messages: list) -> int:
    """Rough token count estimate (~4 chars/token).

    Args:
        messages: Message list.

    Returns:
        Estimated token count.
    """
    return len(json.dumps(messages, default=str, ensure_ascii=False)) // 4


def _is_tool_success(result: str) -> bool:
    """Return True if the tool result does not look like an error response."""
    try:
        data = json.loads(result)
        if isinstance(data, dict) and data.get("status") == "error":
            return False
    except (json.JSONDecodeError, TypeError) as e:
        from app.core.logger import get_logger
        logger = get_logger(__name__)
        logger.warning("loop_base.py._is_tool_success: %s", e)
    return True


def _normalize_tool_run_dir(args: dict[str, Any], memory_run_dir: str | None) -> dict[str, Any]:
    """Normalize ``run_dir`` in tool args to an absolute path when possible.

    If the model supplies a relative ``run_dir`` (for example ``"."`` or
    ``"risk_parity_run"``), resolve it against the active run directory.
    """
    from pathlib import Path

    normalized = dict(args)
    if not memory_run_dir:
        return normalized

    if "run_dir" not in normalized:
        normalized["run_dir"] = memory_run_dir
        return normalized

    run_dir_value = str(normalized["run_dir"]).strip()
    if not run_dir_value:
        normalized["run_dir"] = memory_run_dir
        return normalized

    candidate = Path(run_dir_value)
    if not candidate.is_absolute():
        normalized["run_dir"] = str((Path(memory_run_dir) / candidate).resolve())
    return normalized