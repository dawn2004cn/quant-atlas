from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Hot-reloadable configuration with Redis backend."""


import json
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


class HotReloadConfig:
    """Configuration that can be updated without restarting."""

    def __init__(self, key: str, default_value: object = None, reload_callback: Optional[Callable] = None):
        self.key = key
        self._value = default_value
        self._default = default_value
        self._reload_callback = reload_callback
        self._lock = threading.RLock()
        self._last_updated = datetime.now()

    @property
    def value(self) -> Any:
        """Get current value."""
        with self._lock:
            return self._value

    @value.setter
    def value(self, new_value: object) -> None:
        """Set value and trigger callback."""
        with self._lock:
            self._value = new_value
            self._last_updated = datetime.now()
            if self._reload_callback:
                try:
                    self._reload_callback(new_value)
                except Exception as e:
                    logger.warning(f"Reload callback failed for {self.key}: {e}")

    def reset(self) -> None:
        """Reset to default value."""
        with self._lock:
            self._value = self._default

    def get_age_seconds(self) -> float:
        """Get seconds since last update."""
        return (datetime.now() - self._last_updated).total_seconds()


class ConfigManager:
    """Manager for hot-reloadable configurations using Redis."""

    def __init__(self, redis_url: str = ""):
        self._redis_url = redis_url or get_runtime("REDIS_URL", "")
        self._redis = None
        self._configs: dict[str, HotReloadConfig] = {}
        self._lock = threading.Lock()
        self._subscriber_thread = None
        self._running = False
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            from app.infrastructure.redis_client import RedisClientPool
            self._redis = RedisClientPool.get(self._redis_url).client
            self._redis.ping()
            logger.info("ConfigManager: Redis connected")
        except Exception as e:
            logger.warning(f"ConfigManager: Redis unavailable ({e}), using in-memory only")

    def register(
        self,
        key: str,
        default_value: object,
        reload_callback: Optional[Callable] = None
    ) -> HotReloadConfig:
        """Register a configuration key."""
        with self._lock:
            if key in self._configs:
                return self._configs[key]

            config = HotReloadConfig(key, default_value, reload_callback)
            
            # Try to load from Redis
            if self._redis:
                try:
                    stored = self._redis.get(f"config:{key}")
                    if stored:
                        config.value = json.loads(stored)
                        logger.info(f"Loaded config {key} from Redis")
                except Exception as e:
                    logger.warning(f"Failed to load config {key} from Redis: {e}")

            self._configs[key] = config
            return config

    def get_config_dto(self, key: str) -> Optional[ConfigEntryDTO]:
        """Get config as DTO."""
        from app.domain.dto.config_dto import ConfigEntryDTO
        config = self._configs.get(key)
        if not config:
            return None
        return ConfigEntryDTO(
            key=key,
            value=config.value,
            default=config._default,
            age_seconds=config.get_age_seconds(),
            last_updated=config._last_updated.isoformat()
        )

    def get(self, key: str, default: object = None) -> object:
        """Get configuration value."""
        if key in self._configs:
            return self._configs[key].value
        return default

    def set(self, key: str, value: object, persist: bool = True) -> bool:
        """Set configuration value."""
        if key not in self._configs:
            self.register(key, value)

        self._configs[key].value = value

        # Persist to Redis
        if persist and self._redis:
            try:
                self._redis.set(f"config:{key}", json.dumps(value, default=str))
                logger.info(f"Persisted config {key} to Redis")
                return True
            except Exception as e:
                logger.warning(f"Failed to persist config {key}: {e}")

        return False

    def publish_change(self, key: str, value: object) -> None:
        """Publish config change for other instances."""
        if self._redis:
            try:
                self._redis.publish(f"config:changes", json.dumps({
                    "key": key,
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }))
            except Exception as e:
                logger.debug(f"Failed to publish change: {e}")

    def start_subscriber(self) -> None:
        """Start listening for config changes from other instances."""
        if not self._redis:
            return

        self._running = True
        self._subscriber_thread = threading.Thread(target=self._listen_changes, daemon=True)
        self._subscriber_thread.start()
        logger.info("ConfigManager: Started change listener")

    def _listen_changes(self) -> None:
        """Listen for config changes."""
        pubsub = self._redis.pubsub()
        pubsub.subscribe("config:changes")

        try:
            for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        key = data.get("key")
                        value = data.get("value")

                        if key and key in self._configs:
                            self._configs[key].value = value
                            logger.info(f"Config {key} updated from remote")

                    except Exception as e:
                        logger.warning(f"Failed to process config change: {e}")
        finally:
            # Fix: Ensure pubsub cleanup to prevent Redis connection leaks
            pubsub.close()

    def stop_subscriber(self) -> None:
        """Stop the subscriber."""
        self._running = False
        if self._subscriber_thread:
            self._subscriber_thread.join(timeout=2)

    def list_all(self) -> GenericResponseDTO:
        """List all configurations."""
        return {k: {"value": c.value, "age": c.get_age_seconds()} for k, c in self._configs.items()}


# Global config manager
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def config_value(key: str, default: object = None, reload_callback: Optional[Callable] = None) -> object:
    """Decorator/function to get hot-reloadable config.

    Usage:
        # As function
        threshold = config_value("stock_selection_threshold", 0.5)

        # With callback for hot reload
        def on_threshold_change(new_value):
            StrategyEngine().update_threshold(new_value)

        config_value("threshold", 0.5, on_threshold_change)
    """
    manager = get_config_manager()
    config = manager.register(key, default, reload_callback)
    return config.value


def update_config(key: str, value: object) -> bool:
    """Update config and notify all instances."""
    manager = get_config_manager()
    result = manager.set(key, value, persist=True)
    if result:
        manager.publish_change(key, value)
    return result


__all__ = ["HotReloadConfig", "ConfigManager", "get_config_manager", "config_value", "update_config"]