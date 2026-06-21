"""Agent-App Runtime — Phase 17.
Packages each vertical strategy tool as an installable Agent-App with kernel privilege levels."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable
from uuid import uuid4

from app.core.event_bus import get_event_bus
from app.core.logger import get_logger
from app.core.mesh.global_state_bus import get_global_state_bus

logger = get_logger(__name__)


class PrivilegeLevel(Enum):
    KERNEL = auto()      # risk control, stop-loss — always gets CPU/IO
    SYSTEM = auto()      # core platform features
    USER = auto()        # user-installed apps
    SANDBOX = auto()     # experimental / community apps


class AppStatus(Enum):
    STOPPED = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()


@dataclass
class AgentAppManifest:
    """Manifest for a single Agent-App."""
    app_id: str
    name: str
    description: str
    version: str
    author: str = "system"
    privilege: PrivilegeLevel = PrivilegeLevel.USER
    icon: str = "grid"
    tags: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)  # required capabilities
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAppInstance:
    """Runtime instance of an Agent-App for a specific user."""
    instance_id: str
    app_id: str
    user_id: int
    config: dict[str, Any]
    status: AppStatus = AppStatus.STOPPED
    cpu_quota: float = 0.1  # CPU cores allocated
    memory_quota_mb: int = 64
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentAppRegistry:
    """Central registry for all available Agent-Apps and user instances."""
    
    _apps: dict[str, AgentAppManifest] = {}
    _instances: dict[str, AgentAppInstance] = {}
    _handlers: dict[str, Callable] = {}
    
    @classmethod
    def register_app(cls, manifest: AgentAppManifest, handler: Callable | None = None):
        """Register a new Agent-App type."""
        cls._apps[manifest.app_id] = manifest
        if handler:
            cls._handlers[manifest.app_id] = handler
        logger.info("Agent-App registered: %s v%s (%s)", manifest.name, manifest.version, manifest.privilege.name)
    
    @classmethod
    def install(cls, app_id: str, user_id: int, config: dict | None = None) -> AgentAppInstance:
        """Install an Agent-App for a user."""
        manifest = cls._apps.get(app_id)
        if not manifest:
            raise ValueError(f"Unknown Agent-App: {app_id}")
        
        config = config or {}
        config_schema = manifest.config_schema or {}
        merged = {}
        if config_schema:
            for k, v in config_schema.items():
                merged[k] = config.get(k, v.get("default"))
        instance = AgentAppInstance(
            instance_id=str(uuid4().hex[:12]),
            app_id=app_id,
            user_id=user_id,
            config=merged or config or {},
            status=AppStatus.RUNNING,
            cpu_quota=0.5 if manifest.privilege == PrivilegeLevel.KERNEL else 0.1,
            memory_quota_mb=256 if manifest.privilege == PrivilegeLevel.KERNEL else 64,
        )
        cls._instances[instance.instance_id] = instance
        
        # Register kernel-level apps to GlobalStateBus with high priority
        if manifest.privilege == PrivilegeLevel.KERNEL:
            bus = get_global_state_bus()
            bus.write_state(f"agent_app.{app_id}", {
                "app_id": app_id,
                "user_id": user_id,
                "priority": 100,
                "status": instance.status.name,
            })
        
        logger.info("User %d installed Agent-App %s (instance=%s, privilege=%s)",
                   user_id, manifest.name, instance.instance_id, manifest.privilege.name)
        return instance
    
    @classmethod
    def uninstall(cls, instance_id: str) -> bool:
        instance = cls._instances.pop(instance_id, None)
        if instance:
            logger.info("Uninstalled Agent-App instance %s", instance_id)
            return True
        return False
    
    @classmethod
    def get_installed(cls, user_id: int) -> list[AgentAppInstance]:
        return [i for i in cls._instances.values() if i.user_id == user_id]
    
    @classmethod
    def get_available(cls) -> list[AgentAppManifest]:
        return list(cls._apps.values())
    
    @classmethod
    def invoke(cls, instance_id: str, action: str, payload: dict) -> dict:
        instance = cls._instances.get(instance_id)
        if not instance:
            return {"ok": False, "error": "not_installed"}
        handler = cls._handlers.get(instance.app_id)
        if not handler:
            return {"ok": False, "error": "no_handler"}
        try:
            result = handler(instance, action, payload)
            instance.last_active = datetime.now(timezone.utc).isoformat()
            return {"ok": True, "data": result}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


# ── Built-in Agent-Apps ──────────────────────────────────────────

def _register_builtin_apps():
    """Register default system Agent-Apps."""
    
    # Da Ban Radar (打板雷达) — KERNEL privilege
    AgentAppRegistry.register_app(AgentAppManifest(
        app_id="da_ban_radar",
        name="打板雷达",
        description="实时监控涨停板封单强度、炸板率、连板梯队",
        version="1.0.0",
        privilege=PrivilegeLevel.KERNEL,
        icon="zap",
        tags=["da_ban", "limit_up", "realtime"],
        config_schema={
            "refresh_interval": {"type": "int", "default": 5, "description": "刷新间隔（秒）"},
            "min_limit_up_pct": {"type": "float", "default": 9.5, "description": "最小涨停幅度%"},
        },
    ))
    
    # Grid Trading Bot (网格交易)
    AgentAppRegistry.register_app(AgentAppManifest(
        app_id="grid_trading",
        name="网格交易",
        description="自动低吸高抛网格交易策略",
        version="1.0.0",
        privilege=PrivilegeLevel.SYSTEM,
        icon="grid",
        tags=["grid", "auto_trade", "low_freq"],
        config_schema={
            "grid_levels": {"type": "int", "default": 10, "description": "网格层数"},
            "spread_pct": {"type": "float", "default": 1.5, "description": "格差%"},
        },
    ))
    
    # Wave Band Radar (波段雷达)
    AgentAppRegistry.register_app(AgentAppManifest(
        app_id="wave_band_radar",
        name="波段雷达",
        description="基于量价关系的波段买卖点提示",
        version="1.0.0",
        privilege=PrivilegeLevel.USER,
        icon="activity",
        tags=["wave_band", "swing", "technical"],
        config_schema={
            "sensitivity": {"type": "str", "default": "medium", "description": "灵敏度"},
            "lookback_days": {"type": "int", "default": 60},
        },
    ))
    
    # AI Sentiment Reader (AI 情绪解读)
    AgentAppRegistry.register_app(AgentAppManifest(
        app_id="ai_sentiment",
        name="AI 情绪解读",
        description="基于新闻和公告的市场情绪分析",
        version="1.0.0",
        privilege=PrivilegeLevel.USER,
        icon="message-circle",
        tags=["ai", "sentiment", "nlp"],
        config_schema={
            "sources": {"type": "list", "default": ["news", "announcement"]},
        },
    ))
    
    # Longhu Bang Tracker (龙虎榜追踪)
    AgentAppRegistry.register_app(AgentAppManifest(
        app_id="longhu_tracker",
        name="龙虎榜追踪",
        description="游资动向追踪与席位分析",
        version="1.0.0",
        privilege=PrivilegeLevel.USER,
        icon="target",
        tags=["longhu", "capital", "institution"],
    ))
    
    logger.info("Built-in Agent-Apps registered: %d", len(AgentAppRegistry._apps))


_register_builtin_apps()
