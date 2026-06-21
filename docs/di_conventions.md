# 依赖注入（DI）约定

> 阶段一（R4）产出 · 2026-06-15

## 唯一推荐模式

新服务 **必须** 通过 `app/core/registry.py` 的 `register_factory` 注册：

```python
from app.bootstrap_components.factory_helpers import zero_arg_service
from app.core.registry import register_factory

register_factory(
    "my_service",
    zero_arg_service("app.modules.foo.services.my_service", "MyService"),
)
```

需要依赖其他服务时，使用显式 `_make_*` 工厂函数：

```python
def _make_my_service(reg: Any) -> MyService:
    return MyService(
        market_provider=reg.get_or_none("market_data_provider"),
    )

register_factory("my_service", _make_my_service)
```

## 禁止 / 废弃模式

| 模式 | 状态 | 说明 |
|------|------|------|
| `lambda _: __import__(...)` | ❌ 废弃 | 已用 `factory_helpers.zero_arg_service` 替代（`wiring_system.py`、`wiring_trading.py` 已迁移） |
| `wire_*()` 手动赋值 | ⚠️ 兼容 shim | 仅保留 re-export，新代码勿用 |
| `@register_service` 装饰器 | ⚠️ 冻结 | 不新增；存量逐步迁入 `register_factory` |
| `ServiceInjector.inject()` | ⚠️ 模块内 | 仅限 `ai_agent` 模块内部 |
| 模块 `module.py` 内 `_init_*` 大块逻辑 | ⚠️ 减少 | 复杂装配移到 `wiring_*.py` |

## 文件职责

| 文件 | 职责 |
|------|------|
| `bootstrap_components/wiring_market.py` | 行情、自选股、热点板块 |
| `bootstrap_components/wiring_trading.py` | 交易、组合、风控 |
| `bootstrap_components/wiring_ai.py` | AI、Agent、LLM |
| `bootstrap_components/wiring_system.py` | 系统、协作、用户、网格 |
| `bootstrap_components/factory_helpers.py` | 零参懒加载工厂辅助 |

## 启动校验

Boot 时 `validate_wiring(registry)` 解析全部工厂；日志应输出 resolved 服务数量，无 `REQUIRED services missing`。

## 后续（阶段二）

- 合并 `configure_service_registry()` 双重调用点（`bootstrap.py` / `services.py`）
- `application/events/bridge.py` 语义映射修复（避免全部降级为 `MarketDataUpdatedEvent`）
