from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Swarm配置动态管理服务"""


import yaml
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class SwarmConfigModel:
    """Swarm配置模型"""

    def __init__(
        self,
        id: str,
        name: str,
        title: str,
        description: str,
        agents: list[dict],
        tasks: list[dict],
        variables: list[dict],
        is_active: bool = True,
        version: int = 1,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.title = title
        self.description = description
        self.agents = agents
        self.tasks = tasks
        self.variables = variables
        self.is_active = is_active
        self.version = version
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_yaml(self) -> str:
        """导出为YAML格式"""
        return yaml.dump({
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "agents": self.agents,
            "tasks": self.tasks,
            "variables": self.variables
        }, allow_unicode=True, default_flow_style=False)

    @classmethod
    def from_yaml(cls, yaml_str: str, name: str) -> "SwarmConfigModel":
        """从YAML导入"""
        data = yaml.safe_load(yaml_str)
        return cls(
            id=f"custom_{name}",
            name=data.get("name", name),
            title=data.get("title", name),
            description=data.get("description", ""),
            agents=data.get("agents", []),
            tasks=data.get("tasks", []),
            variables=data.get("variables", [])
        )


class DynamicConfigService:
    """动态配置服务 - 从数据库加载Swarm配置"""

    def __init__(self):
        self._configs: dict[str, SwarmConfigModel] = {}
        self._load_from_db()

    def _load_from_db(self):
        """从数据库加载配置"""
        # 简化版：加载默认配置
        # 实际应从MySQL加载
        pass

    def get_config(self, name: str) -> SwarmConfigModel | None:
        """获取配置"""
        return self._configs.get(name)

    def list_configs(self) -> list[SwarmConfigModel]:
        """列出所有配置"""
        return list(self._configs.values())

    def save_config(self, config: SwarmConfigModel) -> None:
        """保存配置到数据库"""
        config.version += 1
        config.updated_at = datetime.now()
        self._configs[config.name] = config
        logger.info(f"Saved config: {config.name} v{config.version}")

    def create_from_yaml(self, yaml_str: str, name: str) -> SwarmConfigModel:
        """从YAML创建配置"""
        config = SwarmConfigModel.from_yaml(yaml_str, name)
        self.save_config(config)
        return config

    def toggle_active(self, name: str, active: bool) -> bool:
        """切换配置状态（无需重启）"""
        if name in self._configs:
            self._configs[name].is_active = active
            self._configs[name].updated_at = datetime.now()
            logger.info(f"Config {name} active: {active}")
            return True
        return False

    def reload_from_file(self, preset_name: str, file_path: str) -> bool:
        """从文件重新加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_str = f.read()

            config = self.create_from_yaml(yaml_str, preset_name)
            logger.info(f"Reloaded config from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
            return False

    def export_all(self) -> GenericResponseDTO[str, str]:
        """导出所有配置为YAML"""
        return {name: cfg.to_yaml() for name, cfg in self._configs.items()}


def create_dynamic_config_service() -> DynamicConfigService:
    """创建动态配置服务"""
    return DynamicConfigService()