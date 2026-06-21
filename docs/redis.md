# Redis 运维与 Quant Atlas 集群配置

## 副本晋升（运维备忘）

将 `REDIS_HOST` / `REDIS_PORT` 替换为实际主节点地址（与应用 `.env` 中 `TASK_MESSAGE_REDIS_URL` 一致）：

```bash
redis-cli -h <REDIS_HOST> -p <REDIS_PORT>
REPLICAOF NO ONE
INFO replication
```

示例输出：`role:master`，`connected_slaves:0`。

---

## 应用侧 Redis 用途

| 环境变量 | 用途 |
|----------|------|
| `TASK_MESSAGE_REDIS_URL` | Celery / 任务消息、**默认 Mesh 桥接**（`bootstrap` → `ClusterEventBusFacade.ensure_cluster`） |
| `MESH_REDIS_URL` | 显式指定 Mesh Pub/Sub（未设则回退 `TASK_MESSAGE_REDIS_URL`） |
| `EXECUTION_REDIS_URL` | 无界执行队列（`RedisMarketExecutionDriver`） |
| `AUTH_RATE_LIMIT_REDIS_URL` | 登录/注册限流（可选；默认回退 `TASK_MESSAGE_REDIS_URL` / `REDIS_URL`） |
| `API_RATE_LIMIT_ENABLED` | `/api/*` 全局限流开关（默认 `1`） |
| `API_RATE_LIMIT_RPM` | 普通 API 每分钟上限（默认 `100`） |
| `API_AI_RATE_LIMIT_RPM` | `/api/v1/ai*`、`/api/v1/briefing*` 每分钟上限（默认 `10`） |
| `KEY_ENCRYPTION_SALT` | PBKDF2 salt（默认 `quant-atlas-key-encrypt-v1`；**变更后已存密文需重加密**） |
| `MESH_TRANSPORT` | `redis`（默认）\| `memory`（测试）\| `nats` |

`.env` 示例（勿将生产地址提交到仓库）：

```env
TASK_MESSAGE_REDIS_URL=redis://127.0.0.1:6379/0
MESH_ENABLED=1
MESH_NODE_ID=cn-sh-01
MESH_REGION=CN
MESH_TRANSPORT=redis
EVENT_BUS_CLUSTER_MODE=auto
```

也可通过 `get_runtime("REDIS_URL", "")` / `TASK_MESSAGE_REDIS_URL` 统一注入；代码中禁止硬编码内网 IP。

`EVENT_BUS_CLUSTER_MODE`：`auto`（随 `MESH_ENABLED`）\| `cluster` \| `local`。

Decision trace（AI 决策溯源）：键 `quant:decision:trace:{decision_id}`，TTL 7 天；Redis 不可用时回退进程内存。

回测费率、滑点、无风险利率等见 [backtest_config.md](./backtest_config.md)。

---

## Cross-Node EventBus（V9）

- **门面**：`app/core/cluster_event_bus.py` → `get_cluster_event_bus()`
- **启动**：应用 bootstrap 调用 `ensure_cluster(redis_url=settings.task_message_redis_url)`
- **桥接**：`app/core/mesh/bridge.py` 将本地 `EventBus` 订阅事件 fan-out 至 `DistributedEventBus`
- **查询**：`GET /api/v1/system/event-bus/cluster`（需登录）

本地开发无 Redis 时可用 `MESH_TRANSPORT=memory` 跑单元测试。
