from __future__ import annotations

"""Infrastructure adapter for ``ConfigLoaderPort``."""

from typing import Any

from app.domain.ports.config_loader_port import ConfigLoaderPort
from app.infrastructure.config_loader.loader import DynamicConfigLoader


class ConfigLoaderPortAdapter(ConfigLoaderPort):
    def __init__(self) -> None:
        self._loader = DynamicConfigLoader()

    def get_config(self, key: str) -> dict[str, Any]:
        return self._loader.get_config(key)
