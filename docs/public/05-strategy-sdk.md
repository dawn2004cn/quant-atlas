# 05 · SDK 与策略扩展

Quant Atlas 对外可编程入口主要分两类：

1. **`app.sdk` HTTP/脚本客户端**（统一归因、告警、快照等）  
2. **领域 / 模块内扩展**（自定义策略逻辑、工具、Capability）

## 5.1 `app.sdk` 快速上手

```python
from app.sdk import create_client

client = create_client()
```

### 统一归因

```python
report = client.attribution.report(
    strategy_name="demo",
    period="30d",
    positions=[{"symbol": "600519", "value": 100000, "return_pct": 2.0, "sector": "白酒"}],
    factor_exposures={"momentum": 0.15},
    factor_returns={"momentum": 0.04},
)
```

- API：`GET /api/v1/attribution/report`
- 页面：`/app` 下归因看板（或经典 `/attribution-dashboard`）

### 告警

```python
feed = client.alerts.list(min_level="warning")
client.alerts.dispatch(min_level="critical", channel_names=["dingtalk"])
```

### 策略快照

```python
snap = client.snapshots.capture(strategy_name="momentum_v1", label="prod")
client.snapshots.rollback(snap.id, apply_settings=True, apply_code=False)
```

更完整示例见内部速查：[`docs/sdk-ux-quickstart.md`](../sdk-ux-quickstart.md)（工程向，非 SLA）。

## 5.2 策略与工具扩展约定

推荐路径：

| 扩展点 | 做法 |
|--------|------|
| 策略逻辑 | 在 `app/modules/strategy/` 按现有 `IStrategyLogic` / catalog 模式注册 |
| 领域端口 | 在 `app/domain/ports/` 定义 Protocol，基础设施实现 |
| Agent 能力 | `@register_capability` 注册到 CapabilityRegistry（返回含 evidence/confidence） |
| 数据源 | `@data_source` / DataSourceRegistry |

原则：

- **依赖倒置**：应用层只依赖端口  
- **可测试**：纯逻辑放 domain / 小函数，I/O 靠边  
- **可观测**：对外工具输出带证据字段  

## 5.3 示例与测试

```bash
# 单元 / 契约
pytest tests/ -q --tb=line -x

# 路由契约（若脚本可用）
python scripts/audit_api_routes.py
```

若仓库含 `examples/` 策略示例，优先从示例复制再改参数。

## 下一步

- [架构约束](./02-architecture.md)
- [贡献指南](./07-contributing.md)
