from __future__ import annotations
"""Dynamic Configuration Loader for modular business rules."""


import json
import logging
from pathlib import Path
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)

class DynamicConfigLoader:
    """Loads modular configurations from the config/dynamic/ directory."""

    def __init__(self, config_dir: Path = Path("config/dynamic")) -> None:
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_config(self, config_name: str) -> dict[str, Any]:
        """Load a dynamic configuration."""
        path = self.config_dir / f"{config_name}.json"
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config {config_name}: {e}")
            return {}
