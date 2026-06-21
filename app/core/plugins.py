from __future__ import annotations
"""Plugin infrastructure with explicit load reporting."""

import importlib
import os
import pkgutil
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.logger import get_logger

logger = get_logger(__name__)


class QuantPlugin(ABC):
    """Base contract for all Quant Atlas plugins."""

    name: str = ""
    version: str = "1.0.0"
    priority: int = 100

    @property
    def plugin_name(self) -> str:
        return self.name or self.__class__.__name__

    @abstractmethod
    def register(self) -> None:
        """Register services into bootstrap wiring (must not import presentation)."""


@dataclass
class PluginLoadReport:
    loaded: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


class PluginRegistry:
    """Discover and register plugins with env toggles."""

    _last_report: PluginLoadReport | None = None

    @classmethod
    def last_report(cls) -> PluginLoadReport | None:
        return cls._last_report

    @classmethod
    def discover_and_register(cls, package_path: str) -> PluginLoadReport:
        report = PluginLoadReport()
        cls._last_report = report

        if not _plugins_enabled():
            report.skipped.append(f"{package_path} (PLUGINS_ENABLED=0)")
            logger.info("Plugin discovery disabled via PLUGINS_ENABLED")
            return report

        allowlist = _plugins_allowlist()
        try:
            package = importlib.import_module(package_path)
        except Exception as exc:
            report.failed.append((package_path, traceback.format_exc()))
            logger.error("Failed to import plugin package %s: %s", package_path, exc)
            return report

        plugins_to_register: list[QuantPlugin] = []
        for _, name, _is_pkg in pkgutil.iter_modules(package.__path__):
            full_name = f"{package_path}.{name}"
            if allowlist and name not in allowlist:
                report.skipped.append(full_name)
                continue
            try:
                module = importlib.import_module(full_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, QuantPlugin)
                        and attr is not QuantPlugin
                    ):
                        plugins_to_register.append(attr())
            except Exception:
                report.failed.append((full_name, traceback.format_exc()))
                logger.error("Failed to load plugin module %s", full_name, exc_info=True)

        plugins_to_register.sort(key=lambda p: p.priority)
        for plugin in plugins_to_register:
            try:
                plugin.register()
                report.loaded.append(plugin.plugin_name)
                logger.info(
                    "Plugin registered: %s v%s (priority=%s)",
                    plugin.plugin_name,
                    plugin.version,
                    plugin.priority,
                )
            except Exception:
                report.failed.append((plugin.plugin_name, traceback.format_exc()))
                logger.error("Plugin register failed: %s", plugin.plugin_name, exc_info=True)

        if report.failed:
            logger.warning(
                "Plugin load completed with %s failure(s): %s",
                len(report.failed),
                [name for name, _ in report.failed],
            )
        return report


def _plugins_enabled() -> bool:
    raw = (os.getenv("PLUGINS_ENABLED", "1") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _plugins_allowlist() -> set[str] | None:
    raw = (os.getenv("PLUGINS_ALLOWLIST", "") or "").strip()
    if not raw:
        return None
    return {part.strip() for part in raw.split(",") if part.strip()}
