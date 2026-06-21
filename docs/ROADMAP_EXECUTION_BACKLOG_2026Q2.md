# Quant Atlas 12周改造执行清单（可直接拆 Jira）

适用时间窗：2026-04-27 至 2026-07-19（Asia/Shanghai）

## 使用方式
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
| ATLAS-DB-007 | 连接池 | 引入连接池参数（pool_size/max_overflow/recycle） | `app/config.py`, `app/infrastructure/database/` | Backend | 1d | 中 | 切换开关回旧连接实现 | 压测下无连接耗尽 |
| ATLAS-DB-008 | 连接池 | 让 Repository 支持 Session 注入 | `app/bootstrap_components/repositories.py`, `app/infrastructure/repositories/*.py` | Backend | 2d | 中 | 构造函数回退为旧参数 | 关键 repo 支持统一 session |
| ATLAS-CEL-001 | Celery可靠性 | 增加任务确认与抢占参数（acks_late/prefetch） | `app/celery_app.py` | Backend | 0.5d | 中 | 恢复旧 celery.conf | Worker 异常重启不造成重复任务风暴 |
| ATLAS-CEL-002 | Celery可靠性 | 增加通用重试策略模板与超时配置 | `app/celery_app.py`, `app/tasks/*.py` | Backend | 1.5d | 中 | 单任务关闭 autoretry 回退 | 关键任务可控重试，失败可观测 |
| ATLAS-CEL-003 | Celery可靠性 | 增加幂等键存储（task fingerprint） | `app/infrastructure/messaging/`, `app/tasks/` | Backend | 2d | 高 | 关闭幂等检查开关 | 重复投递不重复落库 |
| ATLAS-OBS-001 | 可观测性 | 统一 request_id/task_id 透传 | `app/bootstrap.py`, `app/presentation/api/`, `app/tasks/` | Backend | 1d | 中 | 保留旧日志字段兼容 | 一条业务链路可串起 Web->Task |
| ATLAS-OBS-002 | 可观测性 | 统一结构化日志字段规范 | `app/core/logger.py`, `app/celery_app.py` | Backend | 1d | 低 | 回退 formatter | 日志包含 trace/user/task/resource |
| ATLAS-API-001 | API契约 | 为 3 个核心写接口补 Pydantic 请求模型 | `app/presentation/api/routes_v1_*.py` | Backend | 2d | 中 | 路由回退旧解析 | 非法请求返回一致错误结构 |
| ATLAS-API-002 | API契约 | 建立统一响应模型封装（v2 雏形） | `app/presentation/api/response_builders.py` | Backend | 1d | 中 | 保留 v1 response builder | 新接口输出结构固定 |
| ATLAS-QA-001 | 测试 | 增加 migration + repository 集成测试 | `tests/`, `app/infrastructure/repositories/` | QA/Backend | 2d | 中 | 标记非阻塞并回退代码 | CI 可跑迁移与核心仓储测试 |

## Sprint 2（W5-W8）解耦与并行计算
| ID | Epic | Task | Files | Owner | 估时 | 风险 | Rollback | DoD |
|---|---|---|---|---|---:|---|---|---|
| ATLAS-ARC-001 | 领域解耦 | 盘点 application 直连 infrastructure 依赖并建清单 | `app/application/services/*.py` | Architect | 1d | 低 | 无需回滚 | 形成可追踪清单 |
| ATLAS-ARC-002 | 领域解耦 | 将 `MomentsService` 改为依赖 `domain.ports` | `app/application/services/moments_service.py`, `app/domain/ports.py` | Backend | 1.5d | 中 | 保留旧构造器分支 | service 不再 import infra repo |
| ATLAS-ARC-003 | 领域解耦 | 将 `InvestmentManagerService` 去除 infra 直连 | `app/application/services/investment_manager_service.py` | Backend | 2d | 高 | 切回旧服务实现 | 回放/排期功能回归通过 |
| ATLAS-ARC-004 | 领域解耦 | `tdx/qlib` 服务层抽离转换逻辑到 mapper/adapter | `app/application/services/tdx_*`, `app/infrastructure/mappers/` | Backend | 2d | 中 | 保留旧函数入口 | service 仅编排，不含底层转换细节 |
| ATLAS-ARC-005 | 领域解耦 | 强制应用层依赖端口（lint/check） | `tests/`, `scripts/` | Backend | 1d | 中 | 暂时降级为告警 | CI 阻止新增违规 import |
| ATLAS-CEL-004 | 并行执行 | 为 Qlib 重任务改造 group/chord 切片 | `app/tasks/qlib_data_update.py`, `app/application/services/qlib_pipeline_service.py` | Backend | 2.5d | 高 | 切回单任务执行路径 | 同批任务可并行、汇总结果正确 |
| ATLAS-CEL-005 | 并行执行 | 为扫描任务按标的分片 + 队列隔离 | `app/tasks/scanner_tasks.py`, `app/celery_app.py` | Backend | 2d | 高 | 回切旧队列与串行策略 | 扫描吞吐提升，Web 不受阻塞 |
| ATLAS-CEL-006 | 并行执行 | 建立优先级队列（交易高优先/回测低优先） | `app/celery_app.py` | Backend/DevOps | 1d | 中 | 恢复默认队列 | 任务排队符合优先级预期 |
| ATLAS-CACHE-001 | Redis L1 | 接入 Redis L1 缓存抽象层 | `app/infrastructure/`, `app/config.py` | Backend | 1.5d | 中 | 开关关闭 L1 | 接口可选择命中 L1/L2 |
| ATLAS-CACHE-002 | Redis L1 | 行情快照与信号池结果接入 L1 | `app/application/services/scanner_service.py`, `app/presentation/api/routes.py` | Backend | 1.5d | 中 | 逐路由回退数据库直读 | 热点读延迟显著下降 |
| ATLAS-CACHE-003 | 缓存治理 | 定义 TTL、穿透/击穿保护策略 | `app/infrastructure/cache/*` | Backend | 1d | 中 | 使用最小 TTL 回退 | 缓存故障不影响主链路 |
| ATLAS-CONS-001 | 一致性 | 增加 outbox/event 表与派发任务 | `alembic/versions/*`, `app/tasks/`, `app/infrastructure/` | Backend | 2d | 高 | 关闭 outbox 消费器 | 事务提交与事件发布可追踪 |
| ATLAS-API-003 | API版本治理 | 发布 v2 草案与弃用公告 | `docs/`, `app/presentation/api/` | Architect/Backend | 1d | 低 | 延长兼容窗口 | 有明确 v1->v2 迁移文档 |
| ATLAS-QA-002 | 测试 | 增加 Celery 集成测试（重试/幂等/切片） | `tests/`, `app/tasks/` | QA/Backend | 2d | 中 | 降级为 nightly | 核心任务可靠性可回归 |

## Sprint 3（W9-W12）API标准化与前端演进
| ID | Epic | Task | Files | Owner | 估时 | 风险 | Rollback | DoD |
|---|---|---|---|---|---:|---|---|---|
| ATLAS-API-004 | API标准化 | 将高频接口切到 v2 契约 | `app/presentation/api/routes_v1_*.py`, `app/presentation/api/` | Backend | 2d | 中 | 保留 v1 fallback | v2 覆盖核心交易/研究接口 |
| ATLAS-API-005 | API标准化 | 下线 legacy alias（先白名单） | `app/presentation/api/response_builders.py`, `app/config.py` | Backend | 1.5d | 高 | 重新打开 alias 开关 | 非白名单接口不再返回 legacy 字段 |
| ATLAS-API-006 | API标准化 | 增加 API 契约测试与快照 | `tests/`, `app/presentation/api/` | QA/Backend | 1.5d | 中 | 固定旧快照回退 | 契约变更可自动发现 |
| ATLAS-FE-001 | 前端演进 | 建立 BFF 聚合层（先在 Flask 内） | `app/presentation/api/`, `app/application/services/` | Backend | 2d | 中 | 前端直调原接口 | 新前端仅依赖 BFF |
| ATLAS-FE-002 | 前端演进 | 迁移“消息中心”到组件化前端 | `app/presentation/web/templates/message_center.html`, `static/` | Frontend | 3d | 中 | 保留旧模板路由 | 页面可实时刷新，交互可用 |
| ATLAS-FE-003 | 前端演进 | 迁移“投资经理面板”到组件化前端 | `app/presentation/web/templates/investment_managers*.html`, `static/` | Frontend | 4d | 高 | Feature flag 回切旧页 | 大列表渲染与筛选性能达标 |
| ATLAS-FE-004 | 前端演进 | 迁移“研究流水线页”到组件化前端 | `app/presentation/web/templates/research_pipeline.html`, `static/` | Frontend | 3d | 中 | 回退旧模板 | 任务进度展示稳定 |
| ATLAS-REL-001 | 发布治理 | 增加 feature flag 与灰度开关 | `app/config.py`, `app/bootstrap.py` | Backend/DevOps | 1d | 中 | 全量关停新开关 | 可按接口/页面灰度发布 |
| ATLAS-REL-002 | 发布治理 | 输出数据库迁移回滚手册 | `docs/` | Backend/DBA | 1d | 低 | 无 | 每次上线有明确回滚步骤 |
| ATLAS-SEC-001 | 安全审计 | 核心交易与管理操作补审计日志 | `app/presentation/api/`, `app/application/services/` | Backend | 1.5d | 中 | 降级为只记录关键操作 | 审计日志可追溯操作者与对象 |
| ATLAS-PERF-001 | 压测 | 对 API+Celery+MySQL+Redis 做联合压测 | `scripts/`, `tests/` | QA/DevOps | 2d | 中 | 缩小压测范围 | 输出容量上限与扩容阈值 |
| ATLAS-SLO-001 | 运行指标 | 定义并落地 SLO（API P95/任务成功率） | `docs/`, 监控配置 | Architect/DevOps | 1d | 低 | 保留观测不做门禁 | 有明确告警阈值与报表 |

## 里程碑闸门（Go/No-Go）
1. W4 闸门：Alembic、连接池、Celery 可靠性参数全部通过预发回归。
2. W8 闸门：Qlib/扫描切片并行稳定，重复执行与一致性问题关闭。
3. W12 闸门：v2 覆盖率达标，灰度成功率达标后再推进大规模 legacy 下线。

## 建议 Jira Epic 列表
1. EPIC-DB-MIGRATION：ORM/迁移/连接池
2. EPIC-ASYNC-RELIABILITY：Celery 可靠性与并行
3. EPIC-DOMAIN-DECOUPLING：应用层解耦与端口化
4. EPIC-API-STANDARDIZATION：Pydantic 契约与 v2 发布
5. EPIC-FRONTEND-MODERNIZATION：BFF 与页面组件化迁移
6. EPIC-OBS-SEC-RELEASE：观测、安全、发布与压测

## 建议优先级（P0/P1/P2）
1. P0：ATLAS-DB-001~008, ATLAS-CEL-001~003, ATLAS-OBS-001, ATLAS-QA-001
2. P1：ATLAS-ARC-001~005, ATLAS-CEL-004~006, ATLAS-CACHE-001~003, ATLAS-CONS-001
3. P2：ATLAS-API-004~006, ATLAS-FE-001~004, ATLAS-REL-001~002, ATLAS-PERF-001

