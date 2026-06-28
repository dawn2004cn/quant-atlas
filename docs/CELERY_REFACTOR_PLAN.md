# Celery 任务重构计划

> 基于 2026-06-28 全面审计，覆盖 `app/tasks/` 目录 28 个任务模块 + 13 个基础设施模块。

---

## 1. 现状总览

### 1.1 任务规模

| 维度 | 统计 |
|------|------|
| **任务模块** | 28 个 `.py` 文件（含 `registry.py`, `task_wiring.py`, `worker_db_cleanup.py`） |
| **Celery 任务** | ~40 个（`app.tasks.*` 装饰器注册） |
| **定时 Beat** | 25+ 个 crontab 条目 |
| **基础设施** | `celery_app.py`, `celery_ext.py`, `celery_reliability.py`, `celery_integration.py`, `task_dispatcher.py`, `task_event_hub.py`, `task_message_store.py`, `task_progress_store.py`, `celery_task_admin.py` |
| **测试覆盖** | 7 个测试文件 |
| **文档** | 1 份部署文档（`CELERY_WORKER_DEPLOY.md`） |

### 1.2 依赖架构图

```
API Routes (celery_routes.py)
     |
     v
TaskDispatcher (task_dispatcher.py)
     |
     +-- CeleryTaskDispatcher -> enqueue_task_idempotent()
     |
     v
celery_app.py (Celery app + beat_schedule)
     |
     +-- worker_process_init -> discover_task_modules() + ensure_task_bindings()
     +-- task_prerun -> push start msg + workflow hub
     +-- task_postrun -> push success msg + cleanup
     +-- task_failure -> push failure msg + cleanup

Task workers (app/tasks/*.py)
     |
     +-- task_wiring.py (shared factory functions)
     +-- task_message_store.py (status tracking)
     +-- task_event_hub.py (in-process SSE)
     +-- registry.py (metadata registry)
```

### 1.3 任务分类

| 分类 | 模块 | 任务数 | Beat 数 |
|------|------|--------|---------|
| **数据同步** | `data_backfill_tasks`, `qlib_data_update`, `market_tasks`, `market_history_tasks`, `tdx_dayk_tasks`, `tdx_gpcw_tasks`, `tdx_timescale_sync_tasks`, `questdb_sync_tasks`, `ohlcv_reconciliation_tasks`, `news_backfill_tasks` | ~15 | 15 |
| **交易信号** | `scanner_tasks`, `signal_flag_tasks`, `headline_signal_tasks`, `sniper_tasks` | ~6 | 4 |
| **因子管理** | `factor_lifecycle_tasks`, `factor_ic_alerts`, `factor_decay_tasks` | ~4 | 4 |
| **投资经理** | `investment_manager_tasks`, `moments_tasks`, `moments_agent_reply_tasks` | ~4 | 2 |
| **AI 挖掘** | `auto_alpha_tasks`, `rdagent_tasks` | ~2 | 0 |
| **零售心理** | `retail_psychology_tasks`, `retail_meta_learning_tasks` | ~2 | 3 |
| **系统维护** | `execution_feedback_tasks`, `worker_db_cleanup`, `tracing_tasks` | ~4 | 0 |
| **分析/事件** | `analysis_tasks`, `event_tasks`, `alert_dispatch_tasks` | ~3 | 2 |
| **回测** | `backtest_tasks` | ~2 | 0 |
| **注册管理** | `registry.py`（元数据注册表） | ~25 条目 | 0 |

---

## 2. 发现的问题

### P0 -- 架构性问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **两个 Celery 装饰器风格共存** | `shared_task` vs `@celery_app.task` | `auto_alpha_tasks.py`/`analysis_tasks.py` 用 `shared_task`（全局），其余用 `@celery_app.task`（实例）。`shared_task` 需要 `celery_app.py` 模块级自动发现才能生效，但触发时机靠 `worker_process_init` 信号，不是所有启动路径都执行。 |
| 2 | **Celery app 模块级触发** | `celery_app.py` | `celery_app` 模块导入时就执行了 `worker_process_init` 信号连接 + beat 配置，但 `SKIP_TASK_MODULES` 硬编码。 |
| 3 | **任务模块路径引用混乱** | `celery_app.py` | `task_routes` 中写了 `"app.tasks.trading_tasks.*"`，但 `trading_tasks.py` 不存在。这条路由规则永远不会命中。 |
| 4 | **`event_tasks.py` 明确标记废弃** | `event_tasks.py` | Deprecated -- replaced by core/event_bus.py。文件中 8 个 handler 函数但只注册了 1 个 Celery 任务。 |

### P1 -- 代码质量问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 5 | **非 Celery 函数与 Celery 任务混在同一文件** | 多数 `app/tasks/*.py` | 如 `factor_ic_alerts.py` 中 `run_factor_ic_monitor()`（纯 Python 函数）与 `factor_ic_monitor_tick()`（Celery 任务）混在一起，职责不清。 |
| 6 | **依赖注入方式不统一** | 所有 task 文件 | 有 3 种方式混用：(1) `task_wiring.py` 的工厂函数，(2) 直接 `from X import Y`，(3) 函数内部 import。如 `factor_lifecycle_tasks.py` 在函数体内 `from app.config import get_settings`。 |
| 7 | **无统一 BaseTask / ABC** | 所有 task 文件 | 没有任务基类，输入参数类型全靠 `dict[str, Any]`，返回值也全是 `dict[str, Any]`。没有 `@dataclass` 化的任务契约。 |
| 8 | **`registry.py` 与 Beat 调度双线元数据管理** | `registry.py` + `celery_app.py` | `registry.py` 维护 `TASK_REGISTRY`（25 条元数据），`celery_app.py` 的 `_build_beat_schedule()` 维护 ~25 条 beat 条目。两者互不知晓，元数据不一致。 |
| 9 | **错误处理不统一** | 所有 task 文件 | `factor_lifecycle_tasks.py` 返回 `{"status":"failed"}`，`factor_ic_alerts.py` 返回 `{"ok":True}`，格式不统一。 |
| 10 | **模块级 `if _celery is not None` 守卫** | 5 个文件 | 不一致，部分文件有守卫，部分直接注册。 |

### P2 -- 可维护性问题

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 11 | **`worker_db_cleanup.py` 只有一个函数** | 独立文件 | 4 行逻辑占一个文件，可以合并。 |
| 12 | **`tracing_tasks.py` 注册了 3 个 Celery 任务** |  | OpenTelemetry tracing 可通过中间件自动完成，手动注册的任务在 worker 上很少使用。 |
| 13 | **`sniper_tasks.py` 为空** | 文件无任何 Celery 任务 | 只剩下一个空文件。 |
| 14 | **`_beat_schedule()` 已 230+ 行** | `celery_app.py` | 可读性差，所有 beat 条目在大量 `if get_runtime("X_BEAT")` 中维护。 |
| 15 | **无任务测试覆盖率** | 28 个任务模块只对应 7 个测试文件 | 大部分核心数据同步任务无单元测试。 |
| 16 | **`CeleryTaskDispatcher.dispatch()` 只代理** | `task_dispatcher.py` | 它只是调用 `enqueue_task_idempotent()` 的薄壳。 |

---

## 3. 重构计划

### 阶段 1：架构统一（2-3 天）

| 步骤 | 内容 | 影响文件 | 验证方式 |
|------|------|---------|---------|
| 1.1 | **统一为单一的 `@celery_app.task` 装饰器**。移除所有 `@shared_task` 用法。 | `auto_alpha_tasks.py`, `analysis_tasks.py` | `py_compile` + `celery inspect registered` |
| 1.2 | **移除 `task_routes` 中的死路由**：`trading_tasks.*` 删除。 | `celery_app.py` | 编译通过 |
| 1.3 | **清理 `SKIP_TASK_MODULES`** 确保覆盖所有非任务模块。 | `celery_app.py` | 无新 warning |
| 1.4 | **移除废弃的 `event_tasks.py`** 或将核心 handler 迁移到 `core/event_bus.py`。 | `event_tasks.py`（可选删除） | 确认 `routes` 无引用 |
| 1.5 | **统一 `if _celery is not None` 守卫模式**：所有文件使用一致的守卫。 | 5 个文件 | 编译通过 |
| 1.6 | **清理空文件 `sniper_tasks.py`** 和 `worker_db_cleanup.py`。 | 移除/合并 | 编译通过 |

### 阶段 2：元数据统一（2-3 天）

| 步骤 | 内容 | 影响文件 | 验证方式 |
|------|------|---------|---------|
| 2.1 | **扩展 `BeatRegistry`**：让 `BeatRegistry` 同时管理任务元数据 + beat 调度，替代 `registry.py` 和 `_build_beat_schedule()`。 | `core/celery_ext.py`, `celery_app.py` | 所有 beat 条目注册成功 |
| 2.2 | **迁移 beat 条目**：将 `_build_beat_schedule()` 中 25 条 beat 条目迁移到 `BeatRegistry.register_beat()`。 | `celery_app.py`, `core/celery_ext.py` | beat_schedule 完整性测试 |
| 2.3 | **废弃 `registry.py`**：`TASK_REGISTRY` 由 `BeatRegistry` 派生。 | `registry.py` | 前端 `get_tasks_by_category` 正常 |
| 2.4 | **引入 `@beat_task` 装饰器**（可选）：在任务函数上标记 crontab 元数据。 | 所有 task 文件 | 编译通过 |

### 阶段 3：类型化任务契约（3-5 天）

| 步骤 | 内容 | 影响文件 | 验证方式 |
|------|------|---------|---------|
| 3.1 | **定义 `BaseTask` 抽象基类**：含 `task_id`, `task_name`, `params`, `queue`, `max_retries`, `timeout`。 | `core/task_base.py`（新建） | 编译通过 |
| 3.2 | **定义输入/输出 DTO**：为高频任务创建 `@dataclass` 输入/输出。 | `domain/dto/task_dto.py` | 编译通过 |
| 3.3 | **迁移高频任务**：`scanner_tasks.scanner_core_tick` 等使用 DTO。 | `scanner_tasks.py` | 前端行为不变 |
| 3.4 | **迁移 `task_dispatcher.py`：接受类型化输入**。 | `task_dispatcher.py` | 编译通过 |
| 3.5 | **统一错误返回格式**：所有任务输出为 `TaskResult(status, data, error)`。 | 所有 task 文件 | 80% 任务通过 |

### 阶段 4：依赖注入统一（2-3 天）

| 步骤 | 内容 | 影响文件 | 验证方式 |
|------|------|---------|---------|
| 4.1 | **审计所有 task 文件的依赖创建**：统一通过 `task_wiring.py` 工厂函数，禁止函数体内 import。 | `factor_lifecycle_tasks.py` 等 | 编译通过 |
| 4.2 | **简化 `task_wiring.py`**：清理废弃工厂函数。 | `task_wiring.py` | 编译通过 |

### 阶段 5：测试覆盖（3-5 天）

| 步骤 | 内容 | 影响文件 | 验证方式 |
|------|------|---------|---------|
| 5.1 | **为所有任务模块添加 `tests/tasks/conftest.py`**：统一 mock `celery_app` 和 `task_wiring`。 | `tests/tasks/conftest.py` | 测试通过 |
| 5.2 | **为高频任务添加单元测试**：scanner, signal_flag, data_backfill, tdx_dayk, market_tasks, qlib_data_update。 | `tests/tasks/` | 覆盖率 > 60% |
| 5.3 | **Beat 调度完整性测试**：验证所有 beat 的 `"task"` 键对应已注册的 Celery 任务。 | `tests/bootstrap/test_beat_schedule.py` | 所有 beat 对应注册任务 |
| 5.4 | **集成测试**：用 `task_always_eager=True` 验证幂等性和重试路径。 | `tests/integration/test_celery_reliability.py` | 幂等性测试通过 |

### 阶段 6：任务健康管理（1-2 天）

| 步骤 | 内容 | 影响文件 | 验证方式 |
|------|------|---------|---------|
| 6.1 | **基于 `CeleryHealth` 扩展任务级健康检查**：每个任务上报最后运行时间、耗时、成功率。 | `core/celery_ext.py` | 健康端点返回 |
| 6.2 | **Beat 缺失告警**：检测预定的 beat 任务是否在预期窗口内从未执行。 | `core/celery_ext.py` | 告警日志输出 |

---

## 4. 优先级排序

```
Phase 1 (架构统一)  ---- 高优先级，可立即开始
                          |
                          v
Phase 2 (元数据统一) --- 高优先级，依赖 Phase 1
                          |
                          v
Phase 3 (类型化契约) --- 中优先级，依赖 Phase 1
                          |
                          v
Phase 4 (依赖注入) ---- 中优先级，可并行 Phase 3
                          |
                          v
Phase 5 (测试覆盖) ---- 中/长期，依赖 Phase 1-4
                          |
                          v
Phase 6 (健康管理) ---- 长期，持续优化
```

## 5. 建议首先执行的 3 个动作

1. **清理装饰器不一致**（Phase 1.1-1.3）：5 个文件，统一为 `@celery_app.task`，移除死路由。预计 1-2 小时。
2. **清理废弃文件**（Phase 1.4-1.6）：`sniper_tasks.py`, `event_tasks.py`, `worker_db_cleanup.py`。
3. **审计并统一错误返回格式**（Phase 3.5）：为高频任务实现 `TaskResult` 基类。

---

## 6. 附录：任务文件清单

| 文件 | 任务数 | 注册方式 | 守卫 | Beat 绑定 | 状态 |
|------|--------|---------|------|-----------|------|
| `alert_dispatch_tasks.py` | 1 | 纯函数 | 否 | `ALERT_DISPATCH_CELERY_BEAT` | OK |
| `analysis_tasks.py` | 2 | `@shared_task` | 否 | 否 | 需要改 |
| `auto_alpha_tasks.py` | 3 | `@shared_task` | 否 | 否 | 需要改 |
| `backtest_tasks.py` | 2 | 纯函数 | 否 | 否 | OK |
| `data_backfill_tasks.py` | ~6 | 纯函数 | 否 | 5 个 | OK |
| `event_tasks.py` | 1 | `@celery_app.task` | 模块级 | 否 | 已废弃 |
| `execution_feedback_tasks.py` | 3 | 纯函数 | 否 | 否 | OK |
| `factor_decay_tasks.py` | 1 | 纯函数 | 否 | 否 | OK |
| `factor_ic_alerts.py` | 1 | `@_celery.task` | 模块级 | `FACTOR_IC_CELERY_BEAT` | OK |
| `factor_lifecycle_tasks.py` | 3 | 服务端任务名 | 否 | 3 个 | 函数体内 import |
| `federated_heartbeat_tasks.py` | 1 | 纯函数 | 否 | `FEDERATED_CLUSTER_BEAT` | OK |
| `headline_signal_tasks.py` | 1 | 纯函数 | 否 | `HEADLINE_SIGNAL_CELERY_BEAT` | OK |
| `investment_manager_tasks.py` | 3 | 纯函数 | 否 | `INVESTMENT_MANAGERS_CELERY_BEAT` | OK |
| `market_history_tasks.py` | 2 | 纯函数 | 否 | 否 | OK |
| `market_tasks.py` | 3 | 纯函数 | 否 | 3 个 | OK |
| `moments_agent_reply_tasks.py` | 1 | 纯函数 | 否 | 否 | OK |
| `moments_tasks.py` | 1 | 纯函数 | 否 | `MOMENTS_AFTER_CLOSE_BEAT` | OK |
| `news_backfill_tasks.py` | 3 | 纯函数 | 否 | 2 个 | OK |
| `ohlcv_reconciliation_tasks.py` | 1 | 纯函数 | 否 | `OHLCV_RECONCILIATION_BEAT` | OK |
| `qlib_data_update.py` | 2 | 纯函数 | 否 | 2 个 | OK |
| `questdb_sync_tasks.py` | 2 | 纯函数 | 否 | `QUESTDB_SYNC_BEAT` | OK |
| `rdagent_tasks.py` | 1 | `celery_app.task` | 模块级 | 否 | OK |
| `retail_meta_learning_tasks.py` | 1 | 纯函数 | 否 | `RETAIL_META_LEARNING_BEAT` | OK |
| `retail_psychology_tasks.py` | 1 | 纯函数 | 否 | 2 个 | OK |
| `scanner_tasks.py` | 3 | `@_celery.task` | 模块级 | 2 个 | OK |
| `signal_flag_tasks.py` | 3 | `@_celery.task` | 模块级 | 否 | OK |
| `sniper_tasks.py` | 0 | 空文件 | 否 | 否 | 应删除 |
| `strategy_snapshot_tasks.py` | 1 | 纯函数 | 否 | 否 | OK |
| `tdx_dayk_tasks.py` | 3 | 纯函数 | 否 | 1 个 | OK（别名） |
| `tdx_gpcw_tasks.py` | 3 | 纯函数 | 否 | `TDX_GPCW_DAILY_BEAT` | OK |
| `tdx_timescale_sync_tasks.py` | 1 | 纯函数 | 否 | `TIMESCALE_TDX_SYNC_BEAT` | OK |
| `tracing_tasks.py` | 3 | `@celery_app.task` | 模块级 | 否 | OK |
| `worker_db_cleanup.py` | 1 | 纯函数 | 否 | 否 | OK |
