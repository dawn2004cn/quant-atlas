from __future__ import annotations

"""Strategy Loader - 动态策略加载器。

提供策略插件的动态发现与加载:
- 目录扫描
- 模块导入
- 热重载支持
"""


import ast
import hashlib
import importlib
import logging
import pkgutil
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .protocol import StrategyPlugin
from .registry import StrategyRegistry, get_registry

logger = logging.getLogger(__name__)


# Builtins removed from the sandboxed globals for dynamically-loaded strategy files.
_RESTRICTED_BUILTINS: frozenset[str] = frozenset(
    {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
        "input",
        "print",  # strategies should log via the provided logger only
    }
)

# Function names that are forbidden at the AST level for dynamically-loaded files.
_FORBIDDEN_CALL_NAMES: frozenset[str] = frozenset(
    {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
        "system",
        "popen",
        "run",
        "call",
        "check_output",
    }
)

# Module-level imports are forbidden for dynamically-loaded files; they must
# rely on the safe globals provided by the loader.
_ALLOWED_IMPORT_FROM: frozenset[str] = frozenset(
    {
        "app.domain.strategies.plugin.protocol",
        "app.domain.strategy",
    }
)


class UnsafeStrategyCodeError(RuntimeError):
    """Raised when a strategy file fails sandbox validation."""


class SandboxedModuleLoader:
    """Load a single ``.py`` strategy file inside a restricted sandbox.

    Steps:
        1. SHA-256 signature check against ``StrategySignatureService``.
        2. AST analysis forbidding imports and dangerous calls.
        3. Execution in a namespace with restricted builtins.
    """

    def __init__(self, signature_service: Any | None = None):
        self._signature_service = signature_service

    def _signature_service_instance(self) -> Any:
        if self._signature_service is None:
            from app.modules.system.services.strategy_signature_service import (
                StrategySignatureService,
            )

            self._signature_service = StrategySignatureService()
        return self._signature_service

    def _check_signature(self, file_path: Path) -> None:
        svc = self._signature_service_instance()
        if not svc.is_signed(file_path):
            digest = svc.compute_digest(file_path)
            raise UnsafeStrategyCodeError(
                f"Strategy file {file_path.name} is not signed (sha256={digest}). "
                f"Sign it via StrategySignatureService.sign_file() before loading."
            )

    def _validate_ast(self, source: str, file_path: Path) -> None:
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            raise UnsafeStrategyCodeError(
                f"Strategy file {file_path.name} has invalid syntax: {exc}"
            ) from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                raise UnsafeStrategyCodeError(
                    f"Import statements are not allowed in strategy file {file_path.name}"
                )
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module not in _ALLOWED_IMPORT_FROM:
                    raise UnsafeStrategyCodeError(
                        f"Import from '{module}' is not allowed in strategy file {file_path.name}"
                    )
            if isinstance(node, ast.Call):
                name = self._call_name(node.func)
                if name in _FORBIDDEN_CALL_NAMES:
                    raise UnsafeStrategyCodeError(
                        f"Call to '{name}' is forbidden in strategy file {file_path.name}"
                    )

    @staticmethod
    def _call_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def load(self, file_path: Path) -> types.ModuleType:
        self._check_signature(file_path)
        source = file_path.read_text(encoding="utf-8")
        self._validate_ast(source, file_path)

        module_name = f"_sandboxed_strategy_{file_path.stem}_{hashlib.sha256(str(file_path).encode()).hexdigest()[:8]}"
        module = types.ModuleType(module_name)
        module.__file__ = str(file_path)

        safe_globals = {
            "__name__": module_name,
            "__file__": str(file_path),
            "__builtins__": {
                name: getattr(__builtins__, name)
                for name in dir(__builtins__)
                if name not in _RESTRICTED_BUILTINS
            },
        }
        # Inject safe base classes that strategies are expected to subclass.
        safe_globals["StrategyPlugin"] = StrategyPlugin
        try:
            from app.domain.strategy import BaseStrategy

            safe_globals["BaseStrategy"] = BaseStrategy
        except Exception:
            logger.debug("BaseStrategy not available for plugin sandbox")

        exec(compile(source, str(file_path), "exec"), safe_globals)  # sandboxed plugin loader: restricted builtins + safe_globals only

        # Copy public names into the module.
        for name, obj in safe_globals.items():
            if not name.startswith("__"):
                setattr(module, name, obj)
        return module


class PluginDiscovery:
    """插件发现器

    支持多种发现方式:
    - 目录扫描
    - 模块导入
    - 自定义过滤
    """

    def __init__(
        self,
        search_paths: list[str] | None = None,
        base_class: type = StrategyPlugin,
    ):
        self._search_paths = search_paths or []
        self._base_class = base_class
        self._discovered: list[type] = []

    def discover_from_path(self, path: str) -> list[type]:
        """从目录发现插件

        Args:
            path: 目录路径

        Returns:
            发现的插件类列表
        """
        plugins = []
        path_obj = Path(path)

        if not path_obj.exists():
            logger.warning(f"Path does not exist: {path}")
            return plugins

        # 扫描 Python 文件
        sandbox = SandboxedModuleLoader()
        for file in path_obj.glob("*.py"):
            if file.stem.startswith("_"):
                continue

            try:
                module = sandbox.load(file)

                # 查找插件类
                for name, obj in vars(module).items():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, self._base_class)
                        and obj is not self._base_class
                    ):
                        plugins.append(obj)
                        logger.info(f"Discovered plugin: {name} from {file.name}")

            except UnsafeStrategyCodeError as e:
                logger.warning("Skipped unsigned/unsafe strategy file %s: %s", file.name, e)
            except Exception as e:
                logger.error("Failed to load %s: %s", file.name, e)

        return plugins

    def discover_from_package(self, package_name: str) -> list[type]:
        """从包发现插件

        Args:
            package_name: 包名 (如 app.models)

        Returns:
            发现的插件类列表
        """
        plugins = []

        try:
            package = importlib.import_module(package_name)
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if is_pkg:
                    continue

                try:
                    full_name = f"{package_name}.{module_name}"
                    module = importlib.import_module(full_name)

                    for name, obj in vars(module).items():
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, self._base_class)
                            and obj is not self._base_class
                        ):
                            plugins.append(obj)
                            logger.info(f"Discovered plugin: {name} from {full_name}")

                except Exception as e:
                    logger.debug(f"Skip {module_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to discover from package {package_name}: {e}")

        return plugins

    def discover_all(self) -> list[type]:
        """发现所有可用插件"""
        plugins = []

        # 从搜索路径发现
        for path in self._search_paths:
            plugins.extend(self.discover_from_path(path))

        return plugins


class StrategyLoader:
    """策略加载器

    负责:
    - 发现策略插件
    - 注册到全局注册中心
    - 热重载支持
    """

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
    ):
        self._registry = registry or get_registry()
        self._loaded_classes: dict[str, type] = {}

    def load_from_path(
        self,
        path: str,
        auto_register: bool = True,
    ) -> list[str]:
        """从目录加载插件

        Args:
            path: 目录路径
            auto_register: 是否自动注册

        Returns:
            加载成功的插件 ID 列表
        """
        discovery = PluginDiscovery(base_class=StrategyPlugin)
        classes = discovery.discover_from_path(path)

        loaded_ids = []
        for cls in classes:
            try:
                instance = cls()
                plugin_id = instance.metadata.id

                if auto_register:
                    if self._registry.register(instance):
                        loaded_ids.append(plugin_id)
                        self._loaded_classes[plugin_id] = cls

                logger.info(f"Loaded plugin: {plugin_id}")

            except Exception as e:
                logger.error(f"Failed to instantiate {cls.__name__}: {e}")

        return loaded_ids

    def load_from_package(
        self,
        package_name: str,
        auto_register: bool = True,
    ) -> list[str]:
        """从包加载插件

        Args:
            package_name: 包名
            auto_register: 是否自动注册

        Returns:
            加载成功的插件 ID 列表
        """
        discovery = PluginDiscovery(base_class=StrategyPlugin)
        classes = discovery.discover_from_package(package_name)

        loaded_ids = []
        for cls in classes:
            try:
                instance = cls()
                plugin_id = instance.metadata.id

                if auto_register:
                    if self._registry.register(instance):
                        loaded_ids.append(plugin_id)
                        self._loaded_classes[plugin_id] = cls

                logger.info(f"Loaded plugin: {plugin_id}")

            except Exception as e:
                logger.error(f"Failed to instantiate {cls.__name__}: {e}")

        return loaded_ids

    def load_strategy_models(self) -> list[str]:
        """加载 app.models 中的所有策略

        Returns:
            加载成功的插件 ID 列表
        """
        return self.load_from_package("app.models", auto_register=True)

    def reload_plugin(self, plugin_id: str) -> bool:
        """热重载插件

        Args:
            plugin_id: 插件 ID

        Returns:
            是否重载成功
        """
        # 注销旧插件
        self._registry.unregister(plugin_id)

        # 重新加载类
        cls = self._loaded_classes.get(plugin_id)
        if not cls:
            logger.error(f"Plugin class not found: {plugin_id}")
            return False

        try:
            # 重新实例化并注册
            instance = cls()
            if self._registry.register(instance):
                logger.info(f"Plugin reloaded: {plugin_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to reload {plugin_id}: {e}")
            return False

    def get_loaded_classes(self) -> dict[str, type]:
        """获取已加载的插件类"""
        return self._loaded_classes.copy()


class HotReloadManager:
    """热重载管理器

    监控文件变化并自动重载策略。
    """

    def __init__(
        self,
        loader: StrategyLoader,
        watch_paths: list[str],
        on_reload: Callable[[str], None] | None = None,
    ):
        self._loader = loader
        self._watch_paths = watch_paths
        self._on_reload = on_reload
        self._file_mtimes: dict[str, float] = {}
        self._running = False

    def start(self) -> None:
        """启动监控"""
        self._running = True
        logger.info(f"Hot reload started for: {self._watch_paths}")

    def stop(self) -> None:
        """停止监控"""
        self._running = False
        logger.info("Hot reload stopped")

    def check_and_reload(self) -> list[str]:
        """检查并重载

        Returns:
            重载的插件 ID 列表
        """
        reloaded = []

        for path in self._watch_paths:
            path_obj = Path(path)
            if not path_obj.exists():
                continue

            for file in path_obj.glob("*.py"):
                mtime = file.stat().st_mtime
                key = str(file)

                # 新文件或已修改
                if key not in self._file_mtimes or mtime > self._file_mtimes[key]:
                    self._file_mtimes[key] = mtime
                    logger.debug(f"File changed: {file.name}")

        return reloaded


def create_default_loader() -> StrategyLoader:
    """创建默认加载器

    预设常用搜索路径:
    - app/models
    - app/domain/strategies
    """
    loader = StrategyLoader()

    # 自动加载内置策略
    loader.load_strategy_models()

    return loader
