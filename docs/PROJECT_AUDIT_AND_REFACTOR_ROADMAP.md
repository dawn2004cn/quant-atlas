# Quant Atlas 项目审核结论与重构优化路线图

> 生成日期：2026-06-13  
> 审核范围：项目可行性、设计、规划、编码、测试、部署、上线、运维与生产化成熟度  
> 结论摘要：Quant Atlas 具备成为 AI 增强型量化研究与决策辅助平台的潜力，但当前仍处于“功能原型 + 平台化探索”阶段。上线前必须优先完成生产化治理、安全加固、测试 CI、部署标准化、架构收敛与数据治理。

---

## 1. 总体结论

### 1.1 项目定位建议

Quant Atlas 不建议第一阶段定位成“全自动交易机器人”或“对外公开发布的 AI 投顾产品”。

更稳妥、更可控的产品定位是：

> 面向个人投资者、研究团队和小型投研组织的 AI 增强型量化研究与决策辅助平台。

核心能力应包括：

- 行情、财务、公告、研报等数据统一
- 策略池与策略版本管理
- 回测与绩效评估
- 风控预检查与仓位建议
- AI 分析摘要与证据链
- 用户画像与个性化推荐
- 决策记录、复盘与追踪
- 任务流、数据管线与自动化运维

不建议第一阶段开放：

- 自动交易执行
- 无证据 AI 自动决策
- 高杠杆或高风险策略自动推荐
- 面向公众的开放注册
- 未审计的 Alpha Marketplace / Tokenized Alpha 金融交易能力

---

## 2. 审核结论落地

## 2.1 可行性结论

| 维度 | 当前判断 | 说明 |
|---|---:|---|
| 业务可行性 | 中高 | 已覆盖行情、策略、回测、风控、AI 分析、任务、数据湖等核心业务域 |
| 技术可行性 | 中高 | Flask 应用可启动，服务注册、路由注册、模块注册、事件总线、Celery、Qlib/RD-Agent 管线已有雏形 |
| 工程可行性 | 中 | 功能丰富但复杂度高，存在动态 import、服务路径双轨、路由注册静默失败等问题 |
| 生产可行性 | 中低 | 缺少 Docker、CI/CD、统一密钥治理、限流、监控、回滚、备份、健康检查等上线必要条件 |
| 合规可行性 | 中低 | 若涉及自动交易、AI 投顾、收益承诺、用户资产操作，需要单独合规设计 |

### 结论

项目可以继续推进，但必须从“功能扩张”切换到“工程收敛”。

---

## 2.2 设计审核结论

### 已有优势

1. **模块化方向正确**
   - `app/modules/*/services/` 已承载主要业务服务。
   - 旧 `app/application/services/` 已转为 shim，方向正确。

2. **依赖注入与声明式注册已有基础**
   - `app/core/registry.py` 提供 `ServiceRegistry`、`register_factory`、`register_routes`、`register_module`。
   - 适合进一步拆分为更清晰的注册中心。

3. **事件驱动与任务系统具备扩展空间**
   - Celery、Redis、Event Bus、Task Message Store 等基础设施已存在。
   - 适合支撑数据管线、AI Agent、策略任务、异步扫描等能力。

4. **AI 与证据链能力有差异化价值**
   - User Knowledge、Evidence Graph、Decision Provenance、Prompt Evolution 等能力具备产品化价值。

### 设计问题

| 问题 | 风险 | 证据 |
|---|---|---|
| 注册中心过大 | 单点复杂、难测试、难维护 | `app/core/registry.py:1-773` |
| 服务路径双轨 | 旧 import 复活、维护成本高 | `app/application/services/` shim 与 `app/modules/` 并存 |
| 动态 import / lambda 工厂过多 | 调试困难、错误信息不透明 | `app/bootstrap_components/wiring_market.py:158` |
| 路由注册失败被吞掉 | 启动成功但功能缺失 | `app/presentation/api/routes.py:26-44` |
| 严格启动默认关闭 | 缺失服务不会阻塞部署 | `app/bootstrap_components/service_readiness.py:64-70` |
| 多个限流实现并存 | 安全策略不一致 | `app/core/rate_limiter.py`, `app/presentation/rate_limiting.py`, `app/core/middleware/resilience.py` |
| 非法 import 路径 | 路由预热失败 | `routes_v1_data_optimizer.py:12`, `routes_v1_decision_provenance.py:169`, `routes_v1_quant_ai.py:432` |

---

## 2.3 规划审核结论

当前项目规划文档很多，但存在以下问题：

1. 文档数量大，缺少单一权威路线图
2. 功能规划多，工程治理规划少
3. 缺少明确的上线门禁
4. 缺少按优先级排序的重构计划
5. 缺少每个阶段的验收标准
6. 缺少责任边界和 owner 机制
7. 缺少“哪些功能暂缓”的产品收敛说明

### 建议

建立三层规划体系：

1. **产品路线图**
   - MVP 功能
   - 高级功能
   - 实验功能
   - 暂缓功能

2. **工程路线图**
   - 生产化治理
   - 架构收敛
   - 测试 CI
   - 部署标准化
   - 数据治理
   - 安全加固

3. **上线路线图**
   - 内部开发版
   - 内部测试版
   - 团队试用版
   - 小范围灰度
   - 正式发布

---

## 2.4 编码审核结论

### 必须修复

1. 非法 import 路径
2. 路由注册失败静默吞掉
3. `STRICT_BOOTSTRAP=0`
4. 服务工厂异常吞掉
5. 多个限流实现并存
6. SocketIO CORS 通配符
7. 缺少 HSTS
8. 硬编码 Redis / MySQL 地址
9. `app/core/registry.py` 过大
10. 历史脚本与主平台边界不清

### 建议修复

1. 拆分注册中心
2. 删除旧服务 shim
3. 统一服务工厂写法
4. 增加 API contract 测试
5. 增加启动 smoke test
6. 增加服务工厂测试
7. 增加路由注册断言
8. 增加 `.gitignore`
9. 清理 `node_modules`、`.cargo`、`.pytest_cache`、`instance/*.db`
10. 统一文档入口

---

## 2.5 测试审核结论

当前已有大量测试，但缺少系统化测试分层与 CI 强制。

### 当前问题

| 问题 | 风险 |
|---|---|
| 测试按阶段编号 | 长期维护困难 |
| 缺少覆盖率门禁 | 无法判断回归风险 |
| 缺少 CI | 本地通过不代表主干通过 |
| 缺少启动 smoke test | 路由/服务缺失可能上线 |
| 缺少 API contract 测试 | 前端和 API 契约容易漂移 |
| 缺少安全测试 | 权限、CORS、限流风险难发现 |
| 缺少数据质量测试 | 量化结果可信度不足 |

### 建议测试分层

1. 启动测试
2. 服务工厂测试
3. API smoke test
4. API contract 测试
5. 数据质量测试
6. 安全测试
7. Celery 任务测试
8. 回测回归测试
9. AI 证据链测试
10. 部署 smoke test

---

## 2.6 部署审核结论

当前有部署文档，但缺少自动化部署资产。

### 缺失项

| 缺失项 | 影响 |
|---|---|
| Dockerfile | 无法标准化运行环境 |
| docker-compose.yml | 无法一键启动 Web / Worker / Redis / DB |
| `.env.example` | 环境变量不可控 |
| `.gitignore` | 运行时文件容易污染仓库 |
| CI/CD | 无法自动验证 |
| healthcheck | 无法判断服务是否可用 |
| migration command | 数据库升级不可控 |
| backup/restore | 数据恢复不可控 |
| rollback plan | 上线失败无法快速回退 |
| monitoring dashboard | 生产问题不可观测 |

### 建议最小部署架构

```text
Nginx / Traefik
   |
Flask Web
   |
Redis
   |
Celery Worker
   |
Celery Beat
   |
MySQL / PostgreSQL
   |
Qlib data volume
```

---

## 2.7 上线审核结论

上线前红线：

1. 没有 Docker / docker-compose，不上线
2. 没有 CI/CD，不上线
3. 没有 `.gitignore`，不上线
4. 没有覆盖率门禁，不上线
5. 没有生产密钥治理，不上线
6. SocketIO 仍允许 `cors_allowed_origins="*"`，不上线
7. 没有 HSTS，不上线
8. 没有统一限流，不上线
9. 路由注册失败仍静默吞掉，不上线
10. `STRICT_BOOTSTRAP=0`，不上线
11. 仍有非法 import 导致路由预热失败，不上线
12. 数据库迁移和备份策略不明确，不上线
13. 没有生产监控和告警，不上线
14. 没有回滚方案，不上线

---

## 2.8 安全审核结论

### 高危问题

| 问题 | 证据 | 建议 |
|---|---|---|
| SocketIO CORS 通配符 | `app/bootstrap_components/realtime.py:101` | 改为环境变量白名单 |
| 缺少 HSTS | `app/bootstrap.py:128-145` | 生产环境增加 `Strict-Transport-Security` |
| 硬编码内网地址 | `app/celery_app.py:29`, `app/presentation/api/routes_v1_health.py:61`, `app/infrastructure/cache/global_cache.py:19` | 全部改为环境变量 |
| 多套限流实现 | `app/core/rate_limiter.py`, `app/presentation/rate_limiting.py` | 合并为统一 API 限流 |
| 缺少 CI 安全扫描 | 未发现 `.github/workflows` | 增加 `pip-audit` / `safety` |

---

## 2.9 依赖审核结论

当前依赖存在版本老旧和环境冲突风险。

### 已知风险

| 依赖/环境 | 风险 |
|---|---|
| `Flask==2.0.1` | 版本偏旧，生产安全补丁风险 |
| `pandas==1.5.3` | 版本偏旧 |
| `numpy==1.24.3` | 版本偏旧 |
| LangChain / LangGraph 依赖较多 | 供应链与兼容风险 |
| 当前环境 `pip check` 存在冲突 | 生产安装结果不可控 |

### 建议

1. 增加 `requirements-lock.txt`
2. 使用 `pip-tools` 或 `uv` 锁定依赖
3. 增加 `pip-audit`
4. 分离依赖：
   - `requirements.txt`
   - `requirements-dev.txt`
   - `requirements-qlib.txt`
   - `requirements-rdagent.txt`
   - `requirements-web.txt`
5. Flask 3.x 升级前必须做兼容测试

---

## 3. 重构优化总原则

### 3.1 不再继续堆功能

当前功能已经足够多。下一阶段重点是：

- 收敛
- 验证
- 加固
- 部署
- 文档
- 测试
- 可维护性

### 3.2 先生产化，再架构大改

不要一开始就重写整个平台。

正确顺序：

1. 修复上线阻断项
2. 建立 CI/CD
3. 建立部署资产
4. 建立测试门禁
5. 修复安全红线
6. 再拆分大模块

### 3.3 所有重构必须有验收标准

每个重构任务必须回答：

- 改了哪些文件
- 解决什么问题
- 如何验证
- 如何回滚
- 是否影响现有 API
- 是否需要迁移数据

### 3.4 保持 API 向后兼容

除安全修复外，重构不应破坏已有 API。

建议：

- 新接口先加版本前缀
- 旧接口保留一段时间
- 删除接口前必须公告
- 前端页面通过 feature flag 控制

---

## 4. 重构优化路线图

## Phase 0：冻结与盘点

目标：停止无序扩张，建立重构基线。

时间：1-3 天

### 产出

- 当前功能清单
- 当前 API 清单
- 当前服务清单
- 当前部署依赖清单
- 当前测试清单
- 当前文档入口
- 当前上线风险清单

### 关键动作

1. 暂停新增非关键功能
2. 标记 MVP 功能
3. 标记实验功能
4. 标记暂缓功能
5. 标记必须修复问题

### 验收标准

- 有一份权威功能清单
- 有一份权威风险清单
- 有一份重构优先级列表

---

## Phase 1：上线阻断修复

目标：修复所有阻止上线的基础问题。

时间：1-2 周

### 任务 1.1：修复非法 import 与路由预热失败

重点文件：

- `app/presentation/api/routes_v1_data_optimizer.py`
- `app/presentation/api/routes_v1_decision_provenance.py`
- `app/presentation/api/routes_v1_market_aux.py`
- `app/presentation/api/routes_v1_quant_ai.py`
- `app/presentation/api/routes_v1_system_health.py`
- `app/presentation/api/routes_v1_task_ops.py`
- `app/presentation/api/routes_v1_trade_plan.py`
- `app/presentation/api/routes_v1_user_system.py`

验收：

- 所有 API 路由文件通过 `python -m py_compile`
- 应用启动不再出现 route preload syntax warning

---

### 任务 1.2：生产环境路由注册失败改为 fail-fast

重点文件：

- `app/presentation/api/routes.py`
- `app/bootstrap_components/service_readiness.py`

建议策略：

- 本地开发可以继续 warning
- staging / production 必须 raise
- 启动日志中输出 route name、exception、file、line

验收：

- 路由注册失败在 staging/production 中阻断启动
- 本地开发仍可查看 warning

---

### 任务 1.3：开启严格启动校验

重点文件：

- `app/bootstrap_components/service_readiness.py`
- `app/bootstrap.py`

建议策略：

- 本地默认 `STRICT_BOOTSTRAP=0`
- staging/production 默认 `STRICT_BOOTSTRAP=1`
- `REQUIRED_SERVICE_ATTRS` 增加真正启动必需服务

验收：

- 缺少必需服务时 staging/production 启动失败
- 日志能明确输出缺失服务名称

---

### 任务 1.4：修复 SocketIO CORS 通配符

重点文件：

- `app/bootstrap_components/realtime.py`
- `app/config/settings.py`
- `app/core/runtime_config.py`

建议策略：

```python
allowed = get_runtime("SOCKETIO_ALLOWED_ORIGINS", "").split(",")
SocketIO(app, cors_allowed_origins=allowed, async_mode="threading")
```

验收：

- 生产环境不再使用 `cors_allowed_origins="*"`
- 未授权 origin 无法连接 WebSocket

---

### 任务 1.5：增加 HSTS 与安全头

重点文件：

- `app/bootstrap.py`

建议：

```python
if not settings.debug:
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

验收：

- 生产响应包含 HSTS
- 本地开发不受影响

---

### 任务 1.6：清理硬编码 Redis / MySQL 地址

重点文件：

- `app/celery_app.py`
- `app/presentation/api/routes_v1_health.py`
- `app/infrastructure/cache/global_cache.py`
- `scripts/check_yanbao.py`
- `scripts/update_yanbao.py`
- `scripts/*mysql*.py`

验收：

- 默认值改为 `127.0.0.1` 或空字符串
- 生产地址全部来自环境变量或配置文件

---

## Phase 2：部署标准化

目标：让项目具备可重复部署能力。

时间：1-2 周

### 任务 2.1：新增 `.gitignore`

目标文件：

- `.gitignore`

建议忽略：

```text
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
node_modules/
.cargo/
instance/*.db
instance/*.db-journal
instance/*.db-wal
instance/*.db-shm
logs/
tmp/
.env
*.bak
*.dat
*.dir
celerybeat-schedule.*
dump.rdb
```

验收：

- `git status` 不再显示运行时文件
- 源码、配置模板、文档仍可提交

---

### 任务 2.2：新增 Dockerfile

目标文件：

- `Dockerfile`

建议阶段：

1. Python base image
2. 安装系统依赖
3. 安装 Python 依赖
4. 复制应用
5. 设置工作目录
6. 暴露端口
7. 启动 gunicorn

验收：

- `docker build -t quant-atlas .` 成功
- `docker run --rm quant-atlas python -m py_compile ...` 成功

---

### 任务 2.3：新增 docker-compose

目标文件：

- `docker-compose.yml`
- `.env.example`

建议服务：

```text
redis
postgres 或 mysql
web
worker
beat
```

验收：

- `docker compose up -d redis` 成功
- `docker compose up -d web` 可启动 Flask
- `docker compose up -d worker` 可启动 Celery Worker

---

### 任务 2.4：新增健康检查

建议接口：

- `/api/v1/health`
- `/api/v1/system/health`
- `/api/v1/data-lake/health`

验收：

- Web 容器 healthcheck 可判断服务是否 ready
- Worker 容器可判断是否 alive
- Redis/DB 依赖失败时健康检查失败

---

## Phase 3：CI/CD 与质量门禁

目标：所有变更必须自动验证。

时间：1 周

### 任务 3.1：新增 GitHub Actions

目标文件：

- `.github/workflows/ci.yml`

建议 job：

1. `py-compile`
2. `pytest`
3. `ruff`
4. `pip-check`
5. `app-boot-smoke`
6. `route-smoke`

验收：

- PR 必须通过 CI
- 非法 import 会在 CI 中失败
- 路由注册失败会在 CI 中失败

---

### 任务 3.2：新增 ruff 配置

目标文件：

- `pyproject.toml`
- `.ruff.toml`

建议规则：

- F
- E
- W
- B
- I
- UP

验收：

- `ruff check app tests` 通过
- `ruff format --check app tests` 通过

---

### 任务 3.3：增加 pytest-cov

目标文件：

- `pyproject.toml`
- `.github/workflows/ci.yml`

建议：

```toml
[tool.coverage.run]
source = ["app"]

[tool.coverage.report]
fail_under = 40
```

验收：

- CI 输出覆盖率
- 覆盖率低于阈值时失败

---

### 任务 3.4：增加启动 smoke test

目标文件：

- `tests/smoke/test_app_boot.py`

建议测试：

```python
def test_create_app_boots():
    from app.bootstrap import create_app
    app = create_app()
    assert app is not None
    assert "/api/v1/health" in [rule.rule for rule in app.url_map.iter_rules()]
```

验收：

- CI 中可自动启动应用
- 启动失败会阻断合并

---

## Phase 4：架构收敛

目标：降低复杂度，提升可维护性。

时间：2-4 周

### 任务 4.1：拆分 `app/core/registry.py`

目标文件：

- `app/core/registry.py`
- `app/core/service_registry.py`
- `app/core/factory_registry.py`
- `app/core/route_registry.py`
- `app/core/module_registry.py`

建议迁移：

| 原职责 | 新文件 |
|---|---|
| 服务注册 | `service_registry.py` |
| 工厂注册 | `factory_registry.py` |
| 路由注册 | `route_registry.py` |
| 模块注册 | `module_registry.py` |

验收：

- 原有 import 兼容
- 测试全部通过
- `app/core/registry.py` 只保留兼容 re-export

---

### 任务 4.2：收敛服务工厂

目标文件：

- `app/bootstrap_components/wiring_*.py`

建议：

- 减少 lambda `__import__`
- 使用显式 import
- 工厂失败时 raise 明确异常
- 工厂日志输出服务名与失败原因

验收：

- 服务缺失时日志可读
- 服务失败不会被静默吞掉

---

### 任务 4.3：删除旧服务 shim

目标目录：

- `app/application/services/`

前置条件：

- 全仓搜索确认无旧路径 import
- 测试覆盖关键服务
- 文档已更新

验收：

- `app/modules/` 是唯一业务服务路径
- 删除 shim 后测试通过

---

### 任务 4.4：统一限流实现

目标文件：

- `app/core/rate_limiter.py`
- `app/presentation/rate_limiting.py`
- `app/core/middleware/resilience.py`
- `app/domain/aop_decorators.py`

建议：

- 保留 `app/core/rate_limiter.py`
- 其他实现迁移为兼容 wrapper 或删除
- API middleware 统一启用限流

验收：

- 全仓只有一个主要限流实现
- 公共 API 默认启用限流
- 可配置白名单

---

## Phase 5：测试体系升级

目标：让测试真正保护核心能力。

时间：2-4 周

### 任务 5.1：重构测试组织

目标目录：

- `tests/`

建议结构：

```text
tests/
  smoke/
  unit/
  integration/
  api/
  security/
  data_quality/
  deployment/
```

验收：

- 测试按领域组织
- 慢测试标记 `slow`
- 集成测试标记 `integration`

---

### 任务 5.2：增加 API contract 测试

目标文件：

- `tests/api/test_core_api_contracts.py`

建议覆盖：

- `/api/v1/health`
- `/api/v1/data-lake/health`
- `/api/v1/moments/feed`
- `/api/v1/investment-managers/leaderboard`
- `/api/v1/strategy/wizard/templates`

验收：

- 每个核心 API 有状态码、字段、错误码断言

---

### 任务 5.3：增加服务工厂测试

目标文件：

- `tests/unit/test_service_factories.py`

建议覆盖：

- `data_lake_manager`
- `moments_service`
- `investment_manager_service`
- `strategy_wizard_service`
- `alpha_marketplace_service`
- `immune_agent_service`

验收：

- 服务可解析
- 缺失依赖时错误明确

---

### 任务 5.4：增加安全测试

目标文件：

- `tests/security/test_socketio_cors.py`
- `tests/security/test_login_required.py`
- `tests/security/test_rate_limit.py`

验收：

- 未登录 API 被拦截
- SocketIO 不允许任意 origin
- 公共 API 有基础限流

---

## Phase 6：数据与模型治理

目标：提高量化结果可信度。

时间：1-2 个月

### 任务 6.1：统一 symbol 规范

目标文件：

- `app/domain/market/symbol.py`
- `app/core/normalizers/symbol_normalizer.py`
- `app/modules/data/services/data_lake_manager.py`

验收：

- 所有行情、策略、回测、AI 输入统一 symbol 规范
- symbol 错误会被明确拒绝

---

### 任务 6.2：统一数据质量规则

目标文件：

- `app/core/mesh/unified_data_lake.py`
- `app/modules/data/services/data_lake_manager.py`

验收：

- NaN、缺口、异常值、重复日期均有统一处理
- 数据质量结果可查询

---

### 任务 6.3：统一回测指标

目标文件：

- `app/domain/backtest/metrics.py`
- `app/modules/strategy/services/strategy/fast_backtest_engine.py`

验收：

- 所有回测输出同一套指标
- 指标定义有文档
- 指标计算可测试

---

### 任务 6.4：统一策略版本

目标文件：

- `app/domain/strategy/strategy_spec.py`
- `app/modules/strategy/services/strategy/strategy_snapshot_hook.py`

验收：

- 每次策略变更有版本记录
- 回测结果可追溯到策略版本

---

## Phase 7：产品收敛

目标：把复杂平台收敛成用户可理解的产品体验。

时间：1-2 个月

### 任务 7.1：定义 MVP 页面

建议 MVP 页面：

1. 登录
2. 工作台
3. 自选股
4. 行情总览
5. 策略池
6. 回测
7. 投资组合
8. 风控预检查
9. AI 分析
10. 决策复盘

验收：

- 用户能在 5 分钟内完成一次研究闭环
- 非 MVP 功能默认隐藏或灰度

---

### 任务 7.2：收敛 API 暴露面

目标文件：

- `app/presentation/api/routes.py`
- `app/presentation/api/v1_context.py`
- `app/core/registry.py`

建议：

- 增加 route metadata
- 增加 `public` / `internal` / `experimental` 标记
- 生产环境默认关闭 experimental API

验收：

- 对外 API 清单明确
- 实验 API 不会默认暴露给所有用户

---

### 任务 7.3：增加产品化风险提示

目标文件：

- `app/presentation/web/templates/`
- `app/modules/ai_agent/services/`

验收：

- AI 分析结果必须带风险提示
- 回测收益不得暗示未来收益
- 策略建议必须有证据链或风险说明

---

## Phase 8：上线与运维

目标：具备小范围灰度能力。

时间：2-4 周

### 任务 8.1：建立监控

建议指标：

- HTTP 5xx
- API latency p95
- Celery queue length
- Celery task failure
- Redis latency
- DB connection pool
- Data pipeline success/failure
- AI task latency
- WebSocket connection count

验收：

- 生产环境有监控看板
- 关键异常有告警

---

### 任务 8.2：建立备份与恢复

目标文件：

- `scripts/backup_db.sh`
- `scripts/restore_db.sh`
- `docs/BACKUP_RESTORE.md`

验收：

- DB 可定期备份
- 备份可恢复
- 恢复流程有演练记录

---

### 任务 8.3：建立上线 checklist

目标文件：

- `docs/RELEASE_CHECKLIST.md`

验收：

- 每次上线前必须逐项确认
- 未通过红线不得上线

---

## 5. 优先级矩阵

| 优先级 | 事项 | 原因 | 目标时间 |
|---|---|---|---|
| P0 | 修复非法 import | 路由预热失败，影响功能可用性 | 1-3 天 |
| P0 | SocketIO CORS | 安全风险 | 1-3 天 |
| P0 | 硬编码 Redis/MySQL | 环境不可移植 | 1 周 |
| P0 | Docker / docker-compose | 无法标准化部署 | 1-2 周 |
| P0 | CI/CD | 无法自动验证 | 1-2 周 |
| P1 | 严格启动校验 | 防止缺失服务上线 | 1 周 |
| P1 | 路由注册 fail-fast | 防止静默功能缺失 | 1 周 |
| P1 | 统一限流 | 防止滥用与 DoS | 1-2 周 |
| P1 | 测试分层 | 降低回归风险 | 2-4 周 |
| P1 | 注册中心拆分 | 降低复杂度 | 2-4 周 |
| P2 | 删除旧服务 shim | 清理技术债 | 2-4 周 |
| P2 | 数据质量治理 | 提高量化可信度 | 1-2 个月 |
| P2 | 产品 MVP 收敛 | 提高可用性 | 1-2 个月 |
| P3 | Alpha Marketplace 高级能力 | 高复杂度、高风险 | 暂缓 |
| P3 | Tokenized Alpha | 合规与产品风险高 | 暂缓 |
| P3 | 全自动交易 | 合规风险高 | 暂缓 |

---

## 6. 30/60/90 天落地计划

## 0-30 天：生产化基础

目标：具备内部可部署、可验证版本。

### 必做

1. 修复非法 import
2. 增加 `.gitignore`
3. 增加 Dockerfile
4. 增加 docker-compose
5. 增加 CI
6. 修复 SocketIO CORS
7. 增加 HSTS
8. 清理硬编码地址
9. 增加启动 smoke test
10. 增加核心 API smoke test

### 验收

- `docker compose up` 可启动 Web
- CI 自动运行
- 核心 API 可访问
- 安全红线全部关闭

---

## 31-60 天：架构与测试收敛

目标：降低维护成本，建立可靠回归体系。

### 必做

1. 拆分 `app/core/registry.py`
2. 收敛服务工厂
3. 删除旧服务 shim
4. 统一限流实现
5. 重构测试目录
6. 增加 API contract 测试
7. 增加服务工厂测试
8. 增加安全测试
9. 增加覆盖率门槛
10. 增加部署 smoke test

### 验收

- 测试按领域组织
- 覆盖率有门槛
- 服务缺失不会静默失败
- 路由注册失败不会静默吞掉

---

## 61-90 天：数据治理与灰度上线

目标：具备团队试用能力。

### 必做

1. 统一 symbol 规范
2. 统一数据质量规则
3. 统一回测指标
4. 统一策略版本
5. 建立监控看板
6. 建立备份恢复
7. 建立上线 checklist
8. 收敛 MVP 页面
9. 增加风险提示
10. 关闭或灰度实验功能

### 验收

- 团队用户可完成一次完整研究闭环
- 数据质量可追踪
- 策略回测可复现
- AI 分析有证据链
- 生产监控可用
- 有回滚方案

---

## 7. 上线门禁

上线前必须满足：

### 代码门禁

- `py_compile` 通过
- `ruff check` 通过
- `ruff format --check` 通过
- `pytest` 通过
- 覆盖率不低于设定阈值
- 无非法 import
- 无 P0 级别安全漏洞

### 部署门禁

- Docker build 通过
- docker-compose 可启动
- healthcheck 通过
- migration 可执行
- backup/restore 已验证

### 安全门禁

- 无硬编码生产密钥
- 无 SocketIO 通配符 CORS
- HSTS 已启用
- 公共 API 有限流
- 登录态和权限校验通过
- 敏感信息不写入日志

### 数据门禁

- 数据质量规则已启用
- symbol 规范已统一
- 回测指标已统一
- 策略版本可追踪
- AI 分析有证据链

### 运维门禁

- 监控看板已上线
- 告警规则已配置
- 备份策略已验证
- 回滚方案已演练
- 上线 checklist 已签署

---

## 8. 建议的文档体系

当前文档很多，建议收敛为以下入口：

```text
docs/
  PROJECT_AUDIT_AND_REFACTOR_ROADMAP.md  # 本文件：总路线图
  PRODUCT_MVP_SCOPE.md                    # MVP 产品范围
  ENGINEERING_ROADMAP.md                  # 工程治理路线图
  RELEASE_CHECKLIST.md                    # 上线检查清单
  DEPLOYMENT_GUIDE.md                     # 部署指南
  SECURITY_HARDENING.md                   # 安全加固指南
  TESTING_STRATEGY.md                     # 测试策略
  DATA_GOVERNANCE.md                      # 数据治理规范
  API_CONTRACT.md                         # API 契约
```

当前已有文档可保留，但必须建立唯一入口，避免规划分散。

---

## 9. 建议的第一批执行任务

### Task 1：修复路由预热非法 import

目标：

- 消除启动时 route preload syntax warning

验证：

```bash
python -m py_compile app\presentation\api\routes_v1_data_optimizer.py app\presentation\api\routes_v1_decision_provenance.py app\presentation\api\routes_v1_market_aux.py app\presentation\api\routes_v1_quant_ai.py app\presentation\api\routes_v1_system_health.py app\presentation\api\routes_v1_task_ops.py app\presentation\api\routes_v1_trade_plan.py app\presentation\api\routes_v1_user_system.py
```

---

### Task 2：修复 SocketIO CORS

目标：

- 生产环境禁止 `cors_allowed_origins="*"`

验证：

- 配置 `SOCKETIO_ALLOWED_ORIGINS`
- 未授权 origin 连接失败
- 授权 origin 连接成功

---

### Task 3：增加 `.gitignore`

目标：

- 防止运行时文件污染仓库

验证：

- `git status` 不再显示 `.venv`、`node_modules`、`instance/*.db`、`__pycache__`

---

### Task 4：增加 Dockerfile 与 docker-compose

目标：

- 一键启动 Web / Worker / Redis / DB

验证：

```bash
docker compose up -d
```

---

### Task 5：增加 CI

目标：

- PR 自动验证

验证：

- `py_compile`
- `pytest`
- `ruff`
- `pip check`
- app boot smoke test

---

### Task 6：开启 staging/production 严格启动

目标：

- 缺失关键服务时阻断启动

验证：

- `STRICT_BOOTSTRAP=1`
- 缺少必需服务时启动失败
- 日志输出缺失服务名称

---

## 10. 最终建议

Quant Atlas 的下一阶段不应继续追求“功能更多”，而应追求“系统可信”。

优先顺序：

1. 修复上线阻断问题
2. 建立部署资产
3. 建立 CI/CD
4. 修复安全红线
5. 建立测试体系
6. 收敛架构复杂度
7. 治理数据与模型
8. 收敛产品 MVP
9. 小范围灰度
10. 再考虑高级金融能力

结论：  
本项目具备继续投入价值，但必须先完成生产化与工程治理。只有在 P0/P1 问题关闭后，才适合进入团队试用或小范围灰度上线。
