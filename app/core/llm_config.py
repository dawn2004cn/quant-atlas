"""
LLM 统一配置适配器：支持本地模型（Ollama / vLLM）与 OpenAI / DeepSeek。
通过环境变量控制所有 Agent 模块的模型选择与端点。
统一归口：所有 LLM 配置都从这里获取。

Design Patterns Applied:
- Singleton: LLMFactory singleton instance
- Factory: LLMProviderFactory for creating providers
- Strategy: LLMProviderStrategy for different provider behaviors
- Builder: LLMConfigBuilder for complex configuration
- Observer: LLMConfigObserver for configuration change notifications
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from ..core.runtime_config import get_runtime, get_runtime_float

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMConfig:
    """LLM Configuration Value Object (Immutable)."""
    provider: str
    model: str
    api_key: str
    base_url: str
    timeout: float
    is_local: bool
    temperature: float = 0.7
    max_tokens: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "is_local": self.is_local,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def items(self):
        return self.as_dict().items()

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]


class LLMProviderStrategy(ABC):
    """Strategy pattern for different LLM providers."""

    @abstractmethod
    def create_model(self, config: LLMConfig) -> BaseChatModel:
        """Create LLM model instance."""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model name."""
        pass

    @abstractmethod
    def get_default_url(self) -> str:
        """Get default base URL."""
        pass


class OpenAIProviderStrategy(LLMProviderStrategy):
    """OpenAI provider strategy."""

    def create_model(self, config: LLMConfig) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key if config.api_key != "EMPTY" else None,
            base_url=config.base_url,
            timeout=config.timeout,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def get_default_model(self) -> str:
        return "gpt-4o-mini"

    def get_default_url(self) -> str:
        return "https://api.openai.com/v1"


class DeepSeekProviderStrategy(LLMProviderStrategy):
    """DeepSeek provider strategy."""

    def create_model(self, config: LLMConfig) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key if config.api_key != "EMPTY" else None,
            base_url=config.base_url,
            timeout=config.timeout,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def get_default_model(self) -> str:
        return "deepseek-chat"

    def get_default_url(self) -> str:
        return "https://api.deepseek.com"


class OllamaProviderStrategy(LLMProviderStrategy):
    """Ollama provider strategy."""

    def create_model(self, config: LLMConfig) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key if config.api_key != "EMPTY" else None,
            base_url=config.base_url,
            timeout=config.timeout,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def get_default_model(self) -> str:
        return "llama3.2:3b"

    def get_default_url(self) -> str:
        return "http://localhost:11434/v1"


class CustomProviderStrategy(LLMProviderStrategy):
    """Custom provider strategy."""

    def create_model(self, config: LLMConfig) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key if config.api_key != "EMPTY" else None,
            base_url=config.base_url,
            timeout=config.timeout,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def get_default_model(self) -> str:
        return "qwen2.5"

    def get_default_url(self) -> str:
        return "http://localhost:11434/v1"


class LLMProviderFactory:
    """Factory pattern for LLM provider strategies."""

    _strategies: dict[str, type[LLMProviderStrategy]] = {
        "openai": OpenAIProviderStrategy,
        "deepseek": DeepSeekProviderStrategy,
        "ollama": OllamaProviderStrategy,
        "custom": CustomProviderStrategy,
    }

    @classmethod
    def register_strategy(cls, provider: str, strategy: type[LLMProviderStrategy]) -> None:
        """Register a new provider strategy."""
        cls._strategies[provider.lower()] = strategy

    @classmethod
    def create_strategy(cls, provider: str) -> LLMProviderStrategy:
        """Create provider strategy instance."""
        strategy_class = cls._strategies.get(provider.lower(), OpenAIProviderStrategy)
        return strategy_class()


class LLMConfigObserver(ABC):
    """Observer pattern for configuration changes."""

    @abstractmethod
    def on_config_changed(self, old_config: LLMConfig, new_config: LLMConfig) -> None:
        """Handle configuration change."""
        pass


class LLMConfigSubject:
    """Subject for configuration change notifications."""

    def __init__(self) -> None:
        self._observers: list[LLMConfigObserver] = []

    def attach_observer(self, observer: LLMConfigObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach_observer(self, observer: LLMConfigObserver) -> None:
        self._observers.remove(observer)

    def notify_observers(self, old_config: LLMConfig, new_config: LLMConfig) -> None:
        for observer in self._observers:
            observer.on_config_changed(old_config, new_config)


class LLMConfigBuilder:
    """Builder pattern for complex LLM configuration."""

    def __init__(self) -> None:
        self._provider: str | None = None
        self._model: str | None = None
        self._api_key: str | None = None
        self._base_url: str | None = None
        self._timeout: float | None = None
        self._temperature: float | None = None
        self._max_tokens: int | None = None

    def with_provider(self, provider: str) -> LLMConfigBuilder:
        self._provider = provider
        return self

    def with_model(self, model: str) -> LLMConfigBuilder:
        self._model = model
        return self

    def with_api_key(self, api_key: str) -> LLMConfigBuilder:
        self._api_key = api_key
        return self

    def with_base_url(self, base_url: str) -> LLMConfigBuilder:
        self._base_url = base_url
        return self

    def with_timeout(self, timeout: float) -> LLMConfigBuilder:
        self._timeout = timeout
        return self

    def with_temperature(self, temperature: float) -> LLMConfigBuilder:
        self._temperature = temperature
        return self

    def with_max_tokens(self, max_tokens: int) -> LLMConfigBuilder:
        self._max_tokens = max_tokens
        return self

    def build(self) -> LLMConfig:
        """Build LLMConfig from builder."""
        config = LLMFactory.get_config_from_env()
        return LLMConfig(
            provider=self._provider or config["provider"],
            model=self._model or config["model"],
            api_key=self._api_key or config["api_key"],
            base_url=self._base_url or config["base_url"],
            timeout=self._timeout or config["timeout"],
            is_local=self._provider in ("ollama", "custom") or "localhost" in (self._base_url or config["base_url"]),
            temperature=self._temperature or 0.7,
            max_tokens=self._max_tokens,
        )


class LLMFactory:
    """
    LLM 统一工厂：所有 Agent 共享同一个 LLM 配置入口。
    使用环境变量控制：
    - LLM_PROVIDER: 模型提供商 (openai, deepseek, ollama, custom)
    - LLM_MODEL: 模型名称 (gpt-4o-mini, deepseek-coder, qwen2.5, etc.)
    - LLM_API_KEY: API 密钥
    - LLM_BASE_URL: 接口地址 (本地模型如 http://localhost:11434/v1)
    - LLM_TIMEOUT: 请求超时秒数 (默认 120)

    Patterns Applied:
    - Singleton: Single instance of LLM model
    - Factory: Creates provider strategies
    - Observer: Notifies on configuration changes
    """

    _instance: BaseChatModel | None = None
    _config: dict[str, Any] = {}
    _subject = LLMConfigSubject()

    @classmethod
    def get_config_from_env(cls) -> dict[str, Any]:
        """从环境变量获取原始配置字典。"""
        provider = get_runtime("LLM_PROVIDER", "").lower() or "openai"
        strategy = LLMProviderFactory.create_strategy(provider)

        model = get_runtime("LLM_MODEL") or get_runtime("OPENAI_MODEL") or get_runtime("LLM_API_KEY") or get_runtime("OPENAI_API_KEY") or "EMPTY"
        base_url = get_runtime("LLM_BASE_URL") or get_runtime("OPENAI_BASE_URL") or strategy.get_default_url()
        timeout = get_runtime_float("LLM_TIMEOUT", 120.0)
        api_key = get_runtime("LLM_API_KEY") or get_runtime("OPENAI_API_KEY") or "EMPTY"

        is_local = "localhost" in base_url or "127.0.0.1" in base_url

        return {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "timeout": timeout,
            "is_local": is_local,
        }

    @classmethod
    def get_config(cls) -> LLMConfig:
        """获取当前 LLM 配置（不创建实例）。"""
        try:
            resolved = cls._get_resolved_config_from_provider_service()
            if resolved is not None:
                return LLMConfig(
                provider=resolved.provider,
                model=resolved.model_name,
                api_key=resolved.api_key or "EMPTY",
                base_url=resolved.base_url or "",
                timeout=float(resolved.timeout_sec),
                is_local="localhost" in (resolved.base_url or "") or "127.0.0.1" in (resolved.base_url or ""),
                temperature=resolved.temperature,
                max_tokens=resolved.max_tokens,
            )
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        if cls._config:
            provider = cls._config.get("provider", "openai")
            return LLMConfig(
                provider=provider,
                model=cls._config.get("model", "gpt-4o-mini"),
                api_key=cls._config.get("api_key", "EMPTY"),
                base_url=cls._config.get("base_url", ""),
                timeout=cls._config.get("timeout", 120.0),
                is_local=cls._config.get("is_local", False),
            )

        config_dict = cls.get_config_from_env()
        cls._config = config_dict
        return LLMConfig(
            provider=config_dict["provider"],
            model=config_dict["model"],
            api_key=config_dict["api_key"],
            base_url=config_dict["base_url"],
            timeout=config_dict["timeout"],
            is_local=config_dict["is_local"],
        )

    @classmethod
    def get_model(cls, config: LLMConfig | None = None) -> BaseChatModel:
        """获取 LLM 实例（单例）。"""
        if cls._instance is not None and config is None:
            return cls._instance
        if config is None:
            try:
                client = cls._get_model_from_provider_service()
                cls._instance = client
                return client
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
        cfg = config or cls.get_config()
        strategy = LLMProviderFactory.create_strategy(cfg.provider)
        try:
            client = strategy.create_model(cfg)
            from app.core.metrics_helpers import instrument_chat_model

            client = instrument_chat_model(client, model_name=cfg.model, call_type="chat")
            if config is None:
                cls._instance = client
            return client
        except ImportError as exc:
            raise RuntimeError("需要安装 langchain-openai: pip install langchain-openai") from exc

    @classmethod
    def _get_resolved_config_from_provider_service(cls):
        from app.application.services.llm_provider_service import LlmProviderService
        from app.core.key_encryption import KeyEncryptionService
        from app.infrastructure.repositories.llm_config_repository import SqlAlchemyUserLlmConfigRepository

        user_id = 0
        session_factory = None
        try:
            from flask import current_app, request
            registry = current_app.extensions.get("service_registry")
            if registry is not None:
                service = registry.get_or_none("llm_provider_service")
                if service is not None:
                    if hasattr(request, "quant_atlas_user_id"):
                        user_id = int(request.quant_atlas_user_id)
                    return service.resolve(user_id, "default")
            session_factory = current_app.extensions.get("db_session_factory")
            if hasattr(request, "quant_atlas_user_id"):
                user_id = int(request.quant_atlas_user_id)
        except Exception:
            session_factory = None
        if session_factory is None:
            return None
        kms = KeyEncryptionService()
        repo = SqlAlchemyUserLlmConfigRepository(session_factory(), key_encryption=kms)
        service = LlmProviderService(repo, key_encryption=kms)
        return service.resolve(user_id, "default")

    @classmethod
    def _get_model_from_provider_service(cls) -> BaseChatModel:
        from app.application.services.llm_provider_service import LlmProviderService
        from app.core.key_encryption import KeyEncryptionService
        from app.infrastructure.repositories.llm_config_repository import SqlAlchemyUserLlmConfigRepository

        try:
            from flask import current_app
            registry = current_app.extensions.get("service_registry")
            if registry is not None:
                service = registry.get_or_none("llm_provider_service")
                if service is not None:
                    config = cls._get_resolved_config_from_provider_service()
                    return service.build_client(config)
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        try:
            from flask import current_app
            session_factory = current_app.extensions.get("db_session_factory")
        except Exception:
            session_factory = None
        if session_factory is None:
            raise RuntimeError("llm_provider_service unavailable")
        kms = KeyEncryptionService()
        repo = SqlAlchemyUserLlmConfigRepository(session_factory(), key_encryption=kms)
        service = LlmProviderService(repo, key_encryption=kms)
        config = cls._get_resolved_config_from_provider_service()
        return service.build_client(config)

    @classmethod
    def reset(cls) -> None:
        """重置实例（用于测试或切换模型）。"""
        cls._instance = None
        cls._config = {}

    @classmethod
    def attach_observer(cls, observer: LLMConfigObserver) -> None:
        """Attach configuration change observer."""
        cls._subject.attach_observer(observer)

    @classmethod
    def detach_observer(cls, observer: LLMConfigObserver) -> None:
        """Detach configuration change observer."""
        cls._subject.detach_observer(observer)


def get_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """统一获取 LLM 实例的快捷函数。"""
    return LLMFactory.get_model(config)


def get_llm_for_user(user_id: int = 0) -> BaseChatModel:
    """获取指定用户的 LLM 实例（优先 ProviderService，回退环境变量）。"""
    try:
        from app.application.services.llm_provider_service import LlmProviderService
        from app.core.key_encryption import KeyEncryptionService
        from app.infrastructure.repositories.llm_config_repository import SqlAlchemyUserLlmConfigRepository
        try:
            from flask import current_app

            registry = current_app.extensions.get("service_registry")
            if registry is not None:
                service = registry.get_or_none("llm_provider_service")
                if service is not None:
                    config = service.resolve(int(user_id), "default")
                    return service.build_client(config)
            session_factory = current_app.extensions.get("db_session_factory")
        except Exception:
            session_factory = None
        if session_factory is not None:
            kms = KeyEncryptionService()
            repo = SqlAlchemyUserLlmConfigRepository(session_factory(), key_encryption=kms)
            service = LlmProviderService(repo, key_encryption=kms)
            config = service.resolve(int(user_id), "default")
            return service.build_client(config)
    except Exception:
        logger.warning("Suppressed exception", exc_info=True)
        pass
    return get_llm()


def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return LLMFactory.get_config()


def setup_llm_env() -> dict[str, Any]:
    """
    配置 LLM 环境变量，兼容旧配置。
    自动将旧的环境变量映射到新的统一变量。
    """
    config = LLMFactory.get_config_from_env()

    os.environ["LLM_PROVIDER"] = config["provider"]
    os.environ["LLM_MODEL"] = config["model"]
    os.environ["LLM_API_KEY"] = config["api_key"]
    os.environ["LLM_BASE_URL"] = config["base_url"]
    os.environ["LLM_TIMEOUT"] = str(int(config["timeout"]))

    setup_rdagent_env_compat(config)
    setup_trading_agents_env_compat(config)

    return config


def setup_rdagent_env_compat(config: dict[str, Any]) -> None:
    """兼容旧版 RD-Agent 配置。"""
    os.environ["RDAGENT_MODEL"] = config["model"]
    os.environ["RDAGENT_API_KEY"] = config["api_key"]
    os.environ["RDAGENT_BASE_URL"] = config["base_url"]
    if config["is_local"]:
        os.environ["RDAGENT_USE_LOCAL_LLM"] = "1"


def setup_trading_agents_env_compat(config: dict[str, Any]) -> None:
    """兼容旧版 TradingAgents 配置。"""
    os.environ["TRADING_AGENTS_MODEL"] = config["model"]
    if config["is_local"]:
        os.environ["TRADING_AGENTS_USE_LOCAL"] = "1"


def get_quant_prompt_enhancement() -> str:
    """量化专用的增强 Prompt 片段。"""
    return """
### QUANT SPECIALIST INSTRUCTIONS ###
1. Always use Qlib-compatible expressions (e.g., $close, Ref($close, 1)).
2. Prefer vectorized operations over loops.
3. Ensure factors are cross-sectionally normalized (e.g., CS_Rank).
4. Avoid data leakage (never use future data in Ref).
5. In Python code, use Pandas/Numpy idioms that minimize memory usage.
"""


__all__ = [
    'LLMConfig',
    'LLMProviderStrategy',
    'OpenAIProviderStrategy',
    'DeepSeekProviderStrategy',
    'OllamaProviderStrategy',
    'CustomProviderStrategy',
    'LLMProviderFactory',
    'LLMConfigObserver',
    'LLMConfigSubject',
    'LLMConfigBuilder',
    'LLMFactory',
    'get_llm',
    'get_llm_for_user',
    'get_llm_config',
    'setup_llm_env',
    'setup_rdagent_env_compat',
    'setup_trading_agents_env_compat',
    'get_quant_prompt_enhancement',
]
