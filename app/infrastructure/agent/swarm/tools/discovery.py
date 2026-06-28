"""Tool discovery and registry building.

Ported from Vibe-Trading.
"""

import importlib
import pkgutil
from collections import deque
from pathlib import Path

from app.infrastructure.agent.swarm.tools_base import BaseTool, ToolRegistry


from app.core.logger import get_logger

logger = get_logger(__name__)

_SUBCLASSES_CACHE: list[type[BaseTool]] | None = None


def _discover_subclasses() -> list[type[BaseTool]]:
    """Import all modules in this package, then collect BaseTool subclasses."""
    global _SUBCLASSES_CACHE
    if _SUBCLASSES_CACHE is not None:
        return _SUBCLASSES_CACHE

    pkg_dir = str(Path(__file__).parent)
    # Note: we need to adjust the import path
    for _, module_name, _ in pkgutil.iter_modules([pkg_dir]):
        if module_name.startswith("_") or module_name == "discovery":
            continue
        try:
            importlib.import_module(f"app.infrastructure.agent.swarm.tools.{module_name}")
        except Exception as exc:
            logger.warning("Skipped app.infrastructure.agent.swarm.tools.%s: %s", module_name, exc)

    classes: list[type[BaseTool]] = []
    queue = deque(BaseTool.__subclasses__())
    while queue:
        cls = queue.popleft()
        if cls.name:
            classes.append(cls)
        queue.extend(cls.__subclasses__())

    _SUBCLASSES_CACHE = classes
    return classes


def build_registry(*, persistent_memory=None) -> ToolRegistry:
    """Build the tool registry via auto-discovery."""
    registry = ToolRegistry()
    for cls in _discover_subclasses():
        try:
            if not cls.check_available():
                logger.info("Tool %s unavailable, skipping", cls.name)
                continue

            # Special handling for RememberTool if needed
            # For now, just instantiate
            registry.register(cls())
        except Exception as exc:
            logger.warning("Failed to register tool %s: %s", cls.name, exc)
    return registry


def build_filtered_registry(tool_names: list[str]) -> ToolRegistry:
    """Build a ToolRegistry with only specified tools."""
    full = build_registry()
    filtered = ToolRegistry()
    for name in tool_names:
        tool = full.get(name)
        if tool:
            filtered.register(tool)
    return filtered
