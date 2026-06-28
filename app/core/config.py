from __future__ import annotations
"""Configuration management with environment layering."""


import os
import yaml
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from app.core.logger import get_logger

logger = get_logger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = ""
    database: str = "quant_atlas"
    pool_size: int = 10
    echo: bool = False


class RedisConfig(BaseModel):
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""


class MarketProviderConfig(BaseModel):
    """Market data provider configuration."""
    provider: str = "em"
    timeout: int = 30
    retry_count: int = 3
    cache_ttl: int = 60


class StrategyConfig(BaseModel):
    """Strategy configuration."""
    enabled_strategies: list[str] = ["MACD", "RSI", "Breakout"]
    max_positions: int = 10
    default_capital: float = 100000.0


class RiskConfig(BaseModel):
    """Risk management configuration."""
    max_position_size: float = 0.2
    max_daily_loss: float = 0.05
    max_leverage: float = 1.0
    enable_circuit_breaker: bool = True
    circuit_failure_threshold: int = 5


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True


class AppConfig(BaseModel):
    """Main application configuration."""
    debug: bool = False
    secret_key: str = ""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    market_provider: MarketProviderConfig = Field(default_factory=MarketProviderConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        extra = "allow"


class ConfigManager:
    """Configuration manager with environment layering."""

    _instance: ConfigManager | None = None
    _config: AppConfig | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """Load configuration from files and environment."""
        base_dir = Path(__file__).parent.parent.parent
        config_dir = base_dir / "config"

        config_data = {}

        default_config = config_dir / "settings.yaml"
        if default_config.exists():
            with open(default_config) as f:
                config_data = yaml.safe_load(f) or {}

        env = os.getenv("APP_ENV", "development")

        env_config = config_dir / f"settings.{env}.yaml"
        if env_config.exists():
            with open(env_config) as f:
                env_data = yaml.safe_load(f) or {}
                config_data = self._merge_config(config_data, env_data)

        self._config = AppConfig(**config_data)
        logger.info(f"Configuration loaded for environment: {env}")

    def _merge_config(self, base: dict, override: dict) -> dict:
        """Merge configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def get_config(self) -> AppConfig:
        """Get the loaded configuration."""
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        keys = key.split(".")
        value = self._config.model_dump()

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    def reload(self):
        """Reload configuration from files."""
        self._load_config()
        logger.info("Configuration reloaded")


_config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get the global configuration."""
    return _config_manager.get_config()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value."""
    return _config_manager.get(key, default)


__all__ = [
    "AppConfig",
    "DatabaseConfig",
    "RedisConfig",
    "MarketProviderConfig",
    "StrategyConfig",
    "RiskConfig",
    "LoggingConfig",
    "ConfigManager",
    "get_config",
    "get_config_value",
]
