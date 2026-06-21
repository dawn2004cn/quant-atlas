# 量化重构执行清单与路线图

> 来源：ROADMAP_EXECUTION_BACKLOG_2026Q2.md

## 适用时间窗：2026-04-27 至 2026-07-19（Asia/Shanghai）

### 使用方式
1. 将每一行任务作为一个 Jira Story/Task。
2. `ID` 作为外部追踪号保留在 Jira 自定义字段。
3. `Owner` 先用角色占位，落地时替换为真实成员。
4. `DoD` 即验收标准，`Rollback` 直接拷贝到变更单。

## Sprint 1（W1-W4）基础设施与稳定性

| ID | Epic | Task | Files | Owner | 估时 | 风险 | Rollback | DoD |
|---|---|---|---|---|---:|---|---|---|
| ATLAS-DB-001 | DB迁移 | 引入 SQLAlchemy/Alembic 基础骨架 | `requirements.txt`, `app/infrastructure/database/` | Backend | 1d | 低 | 移除依赖与配置入口 | 本地可执行 `alembic revision` 与 `upgrade head` |
| ATLAS-DB-002 | DB迁移 | 建立 SQLAlchemy Engine 工厂与配置读取 | `app/config.py`, `app/infrastructure/database/` | Backend | 1d | 中 | 保留旧 `mysql_connect` 分支切回 | 统一 engine/session 可注入 |
| ATLAS-DB-003 | DB迁移 | 将 `users/roles` 从硬编码 DDL 迁移到 Alembic 初版 | `app/infrastructure/database/mysql_client.py`, `alembic/versions/*` | Backend | 1.5d | 中 | 回退到上一 migration revision | 新旧环境升级后表结构一致 |
| ATLAS-DB-004 | DB迁移 | 将 `watchlist/stock_groups` 纳入迁移管理 | `app/infrastructure/repositories/*watchlist*`, `alembic/versions/*` | Backend | 1d | 中 | 回退 revision + 读旧表 | 功能回归通过，数据不丢失 |
| ATLAS-DB-005 | DB迁移 | 将 `investment_managers` 相关表纳入迁移 | `app/infrastructure/repositories/investment_manager_repository.py`, `alembic/versions/*` | Backend | 2d | 高 | 迁移前全量备份，必要时回切旧仓储 | 回放/模拟接口回归通过 |
| ATLAS-DB-006 | DB迁移 | 将 `moments` 相关表纳入迁移 | `app/infrastructure/repositories/moments_repository.py`, `alembic/versions/*` | Backend | 1.5d | 中 | 回退 revision + 切旧 repo | 动态流/评论/点赞正常 |
| ATLAS-CEL-001 | Celery可靠性 | 增加任务确认与抢占参数 | `app/celery_app.py` | Backend | 0.5d | 中 | 恢复旧 celery.conf | Worker 异常重启不造成重复任务风暴 |
| ATLAS-CEL-002 | Celery可靠性 | 增加通用重试策略模板与超时配置 | `app/celery_app.py`, `app/tasks/*.py` | Backend | 1.5d | 中 | 单任务关闭 autoretry 回退 | 关键任务可控重试，失败可观测 |
| ATLAS-CEL-003 | Celery可靠性 | 增加幂等键存储（task fingerprint） | `app/infrastructure/messaging/`, `app/tasks/` | Backend | 2d | 高 | 关闭幂等检查开关 | 重复投递不重复落库 |
| ATLAS-OBS-001 | 可观测性 | 统一 request_id/task_id 透传 | `app/bootstrap.py`, `app/presentation/api/`, `app/tasks/` | Backend | 1d | 中 | 保留旧日志字段兼容 | 一条业务链路可串起 Web->Task |
| ATLAS-OBS-002 | 可观测性 | 统一结构化日志字段规范 | `app/core/logger.py`, `app/celery_app.py` | Backend | 1d | 低 | 回退 formatter | 日志包含 trace/user/task/resource |
| ATLAS-API-001 | API契约 | 为 3 个核心写接口补 Pydantic 请求模型 | `app/presentation/api/routes_v1_*.py` | Backend | 2d | 中 | 路由回退旧解析 | 非法请求返回一致错误结构 |
| ATLAS-QA-001 | 测试 | 增加 migration + repository 集成测试 | `tests/`, `app/infrastructure/repositories/` | QA/Backend | 2d | 中 | 标记非阻塞并回退代码 | CI 可跑迁移与核心仓储测试 |

## Sprint 2（W5-W8）解耦与并行计算

| ID | Epic | Task | Owner | 估时 | 风险 | DoD |
|---|---|---|---|---:|---|---|
| ATLAS-ARC-001 | 领域解耦 | 盘点 application 直连 infrastructure 依赖并建清单 | Architect | 1d | 低 | 形成可追踪清单 |
| ATLAS-ARC-002 | 领域解耦 | 将 `MomentsService` 改为依赖 `domain.ports` | Backend | 1.5d | 中 | service 不再 import infra repo |
| ATLAS-ARC-003 | 领域解耦 | 将 `InvestmentManagerService` 去除 infra 直连 | Backend | 2d | 高 | 回放/排期功能回归通过 |
| ATLAS-ARC-004 | 领域解耦 | `tdx/qlib` 服务层抽离转换逻辑到 mapper/adapter | Backend | 2d | 中 | service 仅编排，不含底层转换细节 |
| ATLAS-ARC-005 | 领域解耦 | 强制应用层依赖端口（lint/check） | Backend | 1d | 中 | CI 阻止新增违规 import |
| ATLAS-CEL-004 | 并行执行 | 为 Qlib 重任务改造 group/chord 切片 | Backend | 2.5d | 高 | 同批任务可并行、汇总结果正确 |
| ATLAS-CEL-005 | 并行执行 | 为扫描任务按标的分片 + 队列隔离 | Backend | 2d | 高 | 扫描吞吐提升，Web 不受阻塞 |

---
*本文档保留原始格式，供拆分 Jira/飞书任务使用。*
