from __future__ import annotations
"""Agent Configuration - Centralized agent settings management.

This module implements from midify_plan13.md optimization:
- AgentConfig: Central configuration for all agent settings
- Load from config.yaml
- Runtime overrides supported

Usage:
    config = get_agent_config()
    timeout = config.agent_timeout_seconds
    llm_tier = config.default_llm_tier
"""


import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMConfig:
    """LLM tier configuration."""
    default_tier: str = "l2_reasoning"
    l1_model: str = "gpt-4o-mini"
    l2_model: str = "gpt-4o"
    l1_max_tokens: int = 1024
    l2_max_tokens: int = 4096
    l1_temperature: float = 0.3
    l2_temperature: float = 0.5


@dataclass
class TimeoutConfig:
    """Timeout configuration for agents."""
    agent_timeout_seconds: float = 60.0
    supervisor_timeout_seconds: float = 30.0
    analyst_timeout_seconds: float = 90.0
    risk_manager_timeout_seconds: float = 45.0
    tool_timeout_seconds: float = 20.0


@dataclass
class RetryConfig:
    """Retry configuration for agent resilience."""
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 2


@dataclass
class BlackboardConfig:
    """Evidence blackboard configuration."""
    enable_redis: bool = False
    redis_host: str = os.environ.get("REDIS_HOST", "127.0.0.1")
    redis_port: int = 6379
    redis_db: int = 0
    local_ttl_seconds: int = 300
    redis_ttl_seconds: int = 3600


@dataclass
class MemoryConfig:
    """Agent memory configuration."""
    enable_persistence: bool = True
    db_path: str = "data/agents/agent_memory.db"
    auto_persist_interval_seconds: int = 60


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enable_telemetry: bool = True
    log_agent_calls: bool = True
    track_token_usage: bool = True
    dashboard_refresh_seconds: int = 30


@dataclass
class AgentConfig:
    """Complete agent configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    blackboard: BlackboardConfig = field(default_factory=BlackboardConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    parallel_departments: bool = True
    enable_early_exit: bool = True
    enable_weighted_consensus: bool = True
    max_conversation_rounds: int = 30


_default_config: AgentConfig | None = None


def load_agent_config(config_path: str | None = None) -> AgentConfig:
    """Load agent config from YAML file."""
    if config_path is None:
        base_dir = Path(__file__).parent.parent.parent
        config_path = str(base_dir / "config" / "agent_config.yaml")

    if not os.path.exists(config_path):
        return AgentConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return AgentConfig(
            llm=LLMConfig(**data.get("llm", {})),
            timeout=TimeoutConfig(**data.get("timeout", {})),
            retry=RetryConfig(**data.get("retry", {})),
            circuit_breaker=CircuitBreakerConfig(**data.get("circuit_breaker", {})),
            blackboard=BlackboardConfig(**data.get("blackboard", {})),
            memory=MemoryConfig(**data.get("memory", {})),
            monitoring=MonitoringConfig(**data.get("monitoring", {})),
            parallel_departments=data.get("parallel_departments", True),
            enable_early_exit=data.get("enable_early_exit", True),
            enable_weighted_consensus=data.get("enable_weighted_consensus", True),
            max_conversation_rounds=data.get("max_conversation_rounds", 30),
        )
    except Exception as e:
        logger.warning("Failed to load config from %s: %s", config_path, e, exc_info=True)
        return AgentConfig()


def get_agent_config() -> AgentConfig:
    """Get singleton agent config."""
    global _default_config
    if _default_config is None:
        _default_config = load_agent_config()
    return _default_config


def reload_agent_config(config_path: str | None = None) -> AgentConfig:
    """Reload agent config from file."""
    global _default_config
    _default_config = load_agent_config(config_path)
    return _default_config