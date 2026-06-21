# Swarm Service 修复总结

## 问题描述

调用 `/api/v1/agent-swarm/swarm/run` 时出现 500 错误：

```
AttributeError: 'RDAgentRunService' object has no attribute 'start_research_swarm'
```

## 根本原因

路由依赖注入错误地将 `RDAgentRunService` 作为 swarm service 使用，但路由期望的是 `SwarmAgentService`（具有 `start_research_swarm()` 方法）。

问题出在三个地方：

1. **`v1_context.py`** (line 205): `swarm_service=s.rdagent_run_service` — 直接使用 rdagent_run_service
2. **`route_deps.py`** (line 167): `swarm_service=ctx.rdagent_run_service or ctx.swarm_service` — 优先使用 rdagent_run_service
3. **缺少 `wire_swarm_agent_service`**: 没有创建和注入 `SwarmAgentService` 的函数

## 修复方案

### 1. 添加 `wire_swarm_agent_service` 函数

在 `app/bootstrap_components/service_wiring.py` 中添加：

```python
def wire_swarm_agent_service(services: Any) -> None:
    """Quant Atlas 4.0 — Multi-agent swarm orchestration service."""
    if getattr(services, "swarm_agent_service", None) is not None:
        return
    try:
        from app.tasks.task_wiring import create_swarm_agent_service
        services.swarm_agent_service = create_swarm_agent_service()
    except Exception as exc:
        logger.warning("Could not wire swarm_agent_service: %s", exc)
```

### 2. 在主 wiring 函数中调用

在 `wire_all_services` 中添加调用：

```python
wire_swarm_arbiter_service(services)
wire_meta_arbiter_service(services)
wire_swarm_topology_service(services)
wire_swarm_agent_service(services)  # 新增
wire_team_workflow_service(services)
```

### 3. 更新 v1_context.py

```python
# 之前
swarm_service=s.rdagent_run_service,

# 之后
swarm_service=getattr(s, "swarm_agent_service", None) or s.rdagent_run_service,
```

### 4. 更新 route_deps.py

```python
# 之前
swarm_service=ctx.rdagent_run_service or ctx.swarm_service,

# 之后
swarm_service=ctx.swarm_service or ctx.rdagent_run_service,
```

### 5. 更新 require_swarm_service 函数

```python
def require_swarm_service(deps: AiRouteDeps) -> Any:
    from ...application.errors import ValidationError

    svc = deps.swarm_service
    if svc is None:
        svc = deps.rdagent_run_service
    if svc is None:
        raise ValidationError(
            "swarm_service_unavailable",
            details={"service": "swarm_agent_service or rdagent_run_service"},
        )
    return svc
```

## 验证

- ✅ 所有修改的文件编译通过
- ✅ `SwarmAgentService` 正确创建，具有 `start_research_swarm` 方法
- ✅ 所有 route_deps 测试通过 (4/4)

## 服务层次结构

```
SwarmAgentService (正确的 swarm service)
├── swarm_port: SwarmOrchestratorAdapter
│   └── SwarmRuntime + SwarmStore
├── skill_port: ExpertSkillAdapter
│   └── SkillsLoader
└── experiment_repo: IExperimentRepository

RDAgentRunService (RD-Agent 因子挖掘服务，不应作为 swarm service)
└── 用于 RD-Agent 因子生成任务
```

## 影响范围

- `/api/v1/agent-swarm/swarm/run` — 启动多 agent swarm
- `/api/v1/agent-swarm/swarm/status/<run_id>` — 查询 swarm 状态
- `/api/v1/agent-swarm/capabilities` — 列出 swarm 能力
- `/api/v1/agent-swarm/experiments` — 列出实验

所有使用 `require_swarm_service` 的路由现在都会优先使用 `SwarmAgentService`。
