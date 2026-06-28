from __future__ import annotations

"""Port for dynamic configuration loading."""

from typing import Any, Protocol


class ConfigLoaderPort(Protocol):
    def get_config(self, key: str) -> dict[str, Any]:
        ...
