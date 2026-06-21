# Quant Atlas 架构重构计划（2026-06）

> 目标读者：核心开发团队
> 前提：已完成的数据层重构（Domain Port 30+、ToolFacadeService、CapabilityRegistry、ContextModule 声明式路由）已保留，本计划在此基础之上继续推进。

---

## 一、现状诊断：从用户视角出发

### 1.1 用户核心旅程

| 用户角色 | 核心价值主张 | 每日工作流 |
|----------|-------------|-----------|
| **散户投资者 (retailer)** | 单页仪表盘 → AI 三选股 + 情绪守卫 + 影子账户镜像 | 打开首页 → 看今日关注 → 点股票 → 跑回测 → 看 AI 研报 |
| **量化研究员 (researcher)** | 六分析师辩论链 → 证据黑屏板 → 因子工厂 → Qlib 实验 | 提交 ticker → 运行 Research Graph → 审查证据 → 回测策略 |
| **交易员 (trader)** | 回测+实盘约束建模 → 风控前置检查 → 交易指令 | 选股 → 策略配置 → 风控预审 → 模拟/实盘下单 |
| **平台管理员** | 用户管理 → 数据同步管理 → 系统健康 | 监控 Celery 任务 → 管理股票分组 → 管理用户角色 |

### 1.2 核心矛盾

**用户的期望** vs **系统的现实**：

| 用户期望 | 系统现状 |
|---------|---------|
| "点一个 ticker，出完整研报" | 270+ 服务分散在 application/，用户不知道先调哪个 |
| "回测真实A股约束" | 回测代码横跨 `models/`、`application/services/strategy/`、`infrastructure/`、`core/engine.py` |
| "数据可靠新鲜" | 6 条数据源读取链 (MySQL → Timescale → Qlib → TDX → AkShare) + 事实守护进程，用户看不到数据可信度 |
| "AI 建议有根据" | 证据黑屏板存在，但 presentation 层直接跳过 application 调用 infrastructure |
| "一秒钟打开平台" | `create_app()` 245行 + 15个 try/except + 50+ 全局单例 + 双重 DI 系统 |

### 1.3 架构债务清单（按严重度）

| 编号 | 问题 | 严重度 | 影响范围 |
|------|------|--------|---------|
| **D1** | Domain → Infrastructure 导入（2处） | 🔴 致命 | `domain/ports/timeseries_ports.py` 直接导入 `infrastructure.timeseries.ohlcv_history_reader` |
| **D2** | Presentation → Infrastructure 直连（13个文件） | 🔴 高 | 13 个 `routes_v1_*.py` 直接 import `infrastructure.*` |
| **D3** | Application → Infrastructure 直连（100+ 文件） | 🔴 高 | `application/services/helpers/` 40+ 访问层本质是 infrastructure proxy |
| **D4** | 双重 DI 系统共存（ServiceRegistry + 过程式 wire_*） | 🟡 中 | 5000+ 行 wiring 代码、Services god-class、循环导入风险 |
| **D5** | create_app() 上帝函数（245行） | 🟡 中 | 配置、DB、插件、蓝图、安全头、后台任务全在一步 |
| **D6** | 全局可变状态泛滥 | 🟡 中 | `app.extensions` 字典 + `infrastructure_binding.py` 50+ bind_* + 模块级单例 |
| **D7** | 模块目录与 presentation 重复 | 🟡 中 | `app/modules/` 包含与 `application/` 重叠的服务，且 `__init__.py` 缺失 |
| **D8** | 无测试基础设施 | 🔴 高 | 无 pytest 配置、无测试夹具、无 mock 策略 |

---

## 二、重构原则

1. **用户旅程驱动**：每次重构都以"用户能做什么"为出发点，不是"代码在哪个目录"
2. **一次一个阶段**：每阶段完成后系统可运行，不中断日常开发
3. **保留已有正确设计**：Domain Port 接口、ToolFacadeService、CapabilityRegistry 声明式模式是正确的方向
4. **渐进式迁移**：用门面/适配器包裹旧代码，而非直接删除
5. **测试先于变更**：每个阶段先建立测试护栏，再改代码

---

## 三、重构阶段

### 阶段 0：测试护栏（第1-2周）

**目标**：在改任何东西之前，建立运行验证。

#### 3.0.1 任务
- [ ] 配置 pytest（`pyproject.toml` / `pytest.ini`），设置 `pythonpath = ["."]`
- [ ] 为 `app/domain/` 建立纯单元测试（`Entity`、`ValueObject`、`MarketSnapshot`、`PerformanceMetrics`）
- [ ] 为 `app/core/registry.py` 建立单例/工厂测试
- [ ] 为 `app/domain/entities.py` 中 12 个 frozen dataclass 建立序列化/反序列化测试
- [ ] 配置 CI：每次 PR 自动运行 `pytest --co -q`（只收集不运行，验证测试框架正常）
- [ ] 配置 coverage threshold（起步 30%）

#### 3.0.2 交付物
- `tests/` 目录结构
- `pytest.ini` + `conftest.py`（全局 fixtures：in-memory DB、mock repository）
- 50+ 单元测试（domain 层）

---

### 阶段 1：DIP 修复（第3-4周）

**目标**：修复 D1-D3 数据层入侵问题，建立真正的依赖倒置。

#### 3.1.1 D1 修复：Domain → Infrastructure

```
# 当前（错误）：
domain/ports/timeseries_ports.py:191 → from app.infrastructure.timeseries.ohlcv_history_reader import fetch_questdb_ohlcv

# 修复后：
domain/ports/timeseries_ports.py → TimeSeriesDBPort（纯接口）
infrastructure/timeseries/ohlcv_history_reader.py → 实现 TimeSeriesDBPort
```

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 将 `TimeSeriesDBPort` 从 `timeseries_ports.py` 拆出到 `domain/ports/timeseries_port.py` | 新建 |
| 2 | 在 `infrastructure/timeseries/` 下创建 `port_adapter.py` 实现 `TimeSeriesDBPort` | 新建 |
| 3 | `timeseries_ports.py` 的 `QuestDBAdapter` / `ClickHouseAdapter` 改为继承 `TimeSeriesDBPort`，内部委托给基础设施实现 | 修改 |
| 4 | 删除 `timeseries_ports.py` 中对 `infrastructure.*` 的导入 | 修改 |
| 5 | 运行 pytest 验证 | 验证 |

#### 3.1.2 D2 修复：Presentation → Infrastructure

| 违规文件 | 直接导入 | 修复方案 |
|----------|---------|---------|
| `routes_v1_agent_swarm.py` | `infrastructure.agent.swarm_orchestrator_adapter` | 通过 `SwarmOrchestratorPort` 或 application service |
| `routes_v1_investment_committee.py` (5处) | `infrastructure.agent.investment_committee` | 通过 `application/services/research/investment_committee_service.py` |
| `routes_v1_stock.py` | `infrastructure.providers.rust_indicators` | 通过 `IndicatorProvider` port |
| `web/pages_admin.py` | `infrastructure.repositories.factory` | 通过 application service |
| `api/agent_swarm/routes.py` | `infrastructure.agent.swarm.runtime` + `swarm.store` | 通过 `SwarmOrchestratorPort` |

**通用修复模式**：

```python
# 之前（违规）：
# presentation/api/routes_v1_agent_swarm.py
from app.infrastructure.agent.swarm_orchestrator_adapter import SwarmOrchestratorAdapter

@bp.route("/swarm/run", methods=["POST"])
def run_swarm():
    adapter = SwarmOrchestratorAdapter(...)
    return adapter.run()

# 之后（合规）：
# presentation/api/routes_v1_agent_swarm.py
from app.application.services.orchestration.swarm_service import SwarmApplicationService

@bp.route("/swarm/run", methods=["POST"])
def run_swarm():
    service = app.extensions["services"].swarm_service  # 或注入
    return service.run_swarm(request.json)
```

| 步骤 | 操作 |
|------|------|
| 1 | 为每个违规文件，确认对应的 application service 或 port adapter 存在 |
| 2 | 若不存在，先在 application 层创建 use-case service |
| 3 | 修改 route 文件，替换 import |
| 4 | 运行 API 测试验证 |

#### 3.1.3 D3 修复：Application Helpers → Infrastructure Proxy

**核心问题**：`application/services/helpers/` 下 40+ `xxx_access.py` 文件，每个都是 infrastructure 的薄代理。

**修复策略**：分层清理

```
# 清理前：
application/services/helpers/tdx_local_access.py     → infrastructure/external/tdx/ 的代理
application/services/helpers/qlib_access.py           → infrastructure/qlib/ 的代理
application/services/helpers/market_data_provider.py   → domain/ports/market_ports.py 的代理

# 清理后：
# 所有 infrastructure 直连移到 infrastructure/ 层
# application 层只通过 domain ports 通信
application/services/helpers/    → 保留 5-8 个真正的 use-case helpers
                                  其余删除，调用方迁移到 port
infrastructure/adapters/         → 放原 helpers 对应的 adapter 实现
```

| 步骤 | 操作 | 工作量 |
|------|------|--------|
| 1 | 分类：40+ helpers 按功能分组（市场数据/因子/研报/代理） | 1天 |
| 2 | 为每组确认对应的 domain port 是否存在 | 1天 |
| 3 | 将无 port 的 infrastructure 代码迁移到 `infrastructure/adapters/` | 1周 |
| 4 | 修改 application service 通过 port 访问（而非直接 import infrastructure） | 2周 |
| 5 | 删除 `application/services/helpers/` 中已迁移的文件 | 半天 |

---

### 阶段 2：Wiring 统一（第5-7周）

**目标**：消除 D4 双重 DI 系统，统一为 `ServiceRegistry`。

#### 3.2.1 现状分析

```
当前两条路并存：
  路A（新）：@register_service / @register_factory / ServiceRegistry
  路B（旧）：Service class (80+ None attrs) + wire_*() 函数 (5000+行)

wiring_system.py (1226行)
wiring_market.py (1323行)
wiring_ai.py     (400+行)
wiring_trading.py (600+行)
service_wiring.py (514行)
────────────────────
总计 ~4000 行 wiring 代码
```

#### 3.2.2 迁移策略

```
Step 1: 建立 wire → register_service 转换脚本
- 自动将 wire_xxx_service() 中的构造函数调用转换为 @register_service
- 手动处理有依赖注入逻辑的部分

Step 2: 按模块分批迁移
  批次A（低风险）：system 模块（alert_center, system_health, task_pipeline）
  批次B（中风险）：market_data 模块（stock_service, quote 相关）
  批次C（高风险）：ai_agent 模块（research, swarm, tiered_llm）
  批次D（高风险）：trading 模块（portfolio, execution, risk）

Step 3: 删除旧 wiring 系统
- 删除 wiring_*.py (4个文件)
- 删除 Services class（god-class）
- 删除 infrastructure_binding.py（50+ bind_* 函数）
```

#### 3.2.3 `Services` God-Class 替换

```python
# 之前（God-Class）：
class Services:
    user_service: UserService | None = None
    stock_service: StockApplicationService | None = None
    ... # 80+ 个 None 属性

# 之后（typed dependency injection）：
@dataclass
class AppDependencies:
    # 按用户旅程分组
    market: MarketApplication
    research: ResearchApplication
    trading: TradingApplication
    system: SystemApplication
```

**`MarketApplication` 示例**（按用户旅程分组依赖）：

```python
@dataclass(frozen=True)
class MarketApplication:
    """用户查看行情所需的依赖组."""
    stock_service: StockApplicationService
    quote_service: QuoteApplicationService
    panorama_service: PanoramaApplicationService
    sector_service: SectorApplicationService
```

Route handler 签名从：
```python
def stock_detail(symbol: str, services: Services):
    stock = services.stock_service.get_detail(symbol)
```
变为：
```python
def stock_detail(symbol: str, deps: AppDependencies):
    stock = deps.market.stock_service.get_detail(symbol)
```

---

### 阶段 3：create_app() 拆分（第8-9周）

**目标**：将 D5 245行的 `create_app()` 拆分为可测试的步骤。

#### 3.3.1 拆分结构

```
app/
  bootstrap/                    # 新建：组装步骤
    __init__.py                 # create_app() 现在只调用 assemble()
    config_step.py              # 配置加载与验证
    database_step.py            # DB engine, session, migrations
    service_step.py             # ServiceRegistry 初始化（从 wiring 迁移后）
    presentation_step.py        # Blueprint 注册（替换 presentation.py）
    realtime_step.py            # SocketIO 初始化（从 realtime.py 迁移）
    module_step.py              # ContextModule 发现与初始化
    security_step.py            # Security headers, CSP, login manager
    warmup_step.py              # 运行时预热（Qlib 等）
  bootstrap_components/         # 旧文件逐步迁移/删除
```

#### 3.3.2 每个 step 的测试

```python
# tests/unit/test_bootstrap_config_step.py
def test_load_settings_valid_config():
    settings = load_settings()
    assert settings.database.url == "mysql+mysqlconnector://..."

def test_load_settings_missing_optional_section():
    settings = load_settings()
    assert settings.redis.url == ""  # 可选配置为空字符串默认值
```

---

### 阶段 4：全局状态消除（第10-11周）

**目标**：消除 D6 全局可变状态。

#### 3.4.1 迁移矩阵

| 全局状态 | 当前位置 | 迁移目标 |
|---------|---------|---------|
| `app.extensions["db_engine"]` | Flask extensions 字典 | `AppDependencies.database` |
| `app.extensions["service_bundle"]` | Flask extensions 字典 | `AppDependencies` |
| `_tool_facade_service_instance` | `tool_facade_service.py` 模块级 | `ServiceRegistry` 管理生命周期 |
| `_bound` flag | `infrastructure_binding.py` | 删除 — 依赖注入替代 |
| 50+ `bind_*()` 函数 | `infrastructure_binding.py` | 删除 — 所有绑定走 ServiceRegistry |
| `_registry` / `_factories` | `core/registry.py` 全局 dict | 保留但改为模块局部 + 工厂创建时注册 |

#### 3.4.2 `infrastructure_binding.py` 删除方案

```python
# 之前（50+ 全局 bind_* 函数）：
from app.application.services.helpers import market_data_provider
def bind_market_data_provider(provider):
    market_data_provider._instance = provider
    market_data_provider._bound = True

# 之后（通过 ServiceRegistry）：
# 所有 helpers 中的全局变量改为函数参数或实例属性
# infrastructure_binding.py 完全删除
```

---

### 阶段 5：模块系统清理（第12-13周）

**目标**：解决 D7 `app/modules/` 与 `application/` 的重复。

#### 3.5.1 当前混乱

```
app/modules/market_data/
  ├── __init__.py        (空文件)
  ├── routes.py          (重导出 presentation 路由)
  └── module.py          (实际的 ContextModule 声明)

app/modules/ai_agent/
  ├── routes.py          (重导出)
  └── module.py          (实际内容，但缺少 __init__.py)

app/application/services/data/        ← 实际的市场数据服务实现
app/modules/market_data/services/     ← 另一份市场数据服务（可能重复）
```

#### 3.5.2 重组方案

```
# 最终结构：
app/modules/             # 纯上下文模块声明（轻量）
  └── market_data/
      └── module.py      # MarketDataContextModule: depends_on + wire + initialize
      # 删除 __init__.py, routes.py, services/

app/application/services/  # 所有应用服务（单一位置）
  ├── market/            # 重命名自 data/ + market_data/
  ├── research/          # 研究相关
  ├── trading/           # 交易相关
  └── system/            # 系统管理

app/presentation/         # 所有路由（单一位置）
  ├── api/routes_v1_market.py     # 重命名自 routes_v1_stock.py
  ├── api/routes_v1_research.py
  └── web/                 # HTML 页面
```

---

### 阶段 6：用户旅程 API 重构（第14-16周）

**目标**：将 API 从"按数据实体组织"改为"按用户旅程组织"。

#### 3.6.1 当前 API 问题

```
当前 65+ routes_v1_*.py 按数据实体分组：
  routes_v1_stock.py         (676行)  ← 股票数据
  routes_v1_backtest.py      (412行)  ← 回测
  routes_v1_factor.py        (523行)  ← 因子
  routes_v1_agent.py         (387行)  ← AI Agent
  ...
```

#### 3.6.2 按用户旅程重组

```
presentation/api/
  routes_v1_dashboard.py         # 首页仪表盘（AI Top3 + 市场情绪 + 今日关注）
  routes_v1_stock.py             # 股票详情 + K线 + 决策简报条
  routes_v1_backtest.py          # 回测配置 + 执行 + 报告 + 对比
  routes_v1_research.py          # AI 研报（Research Graph + 辩论 + 决策面板）
  routes_v1_screening.py         # 选股 + 信号旗 + 长期选股
  routes_v1_portfolio.py         # 组合管理 + 影子账户 + 投资经理
  routes_v1_admin.py             # 用户管理 + 股票分组 + 任务中心
  routes_v1_health.py            # 系统健康 + 数据新鲜度 + 集成中心
```

每个文件 ≤ 200 行，对应一个用户页面。

---

### 阶段 7：配置统一（第17周）

**目标**：消除 D8 配置碎片化。

#### 3.7.1 现状

| 配置系统 | 文件 | 格式 | 状态 |
|---------|------|------|------|
| AppSettings | `app/config/settings.py` | Pydantic dataclass | 主要使用 |
| RuntimeConfig | `app/core/runtime_config.py` | configparser (.cfg) | Celery beat 等 |
| LegacyConfig | `app/core/config.py` | Pydantic | **疑似未使用** |
| YAML | `config/settings.yaml` | YAML | 未确认是否加载 |
| .env | `.env` | dotenv | 环境变量 |

#### 3.7.2 统一方案

```
保留 AppSettings (Pydantic) 作为唯一配置入口：
  app/config/settings.py       → 完整的 AppConfig dataclass（合并所有设置）
  app/config/providers.py      → 多来源加载：.env > .cfg > YAML > 默认值
  app/config/validate.py       → 环境特定验证（dev/prod/trading）
  app/core/config.py           → 删除（未使用）
  app/core/runtime_config.py   → 迁移到 app/config/providers.py
```

---

## 四、实施顺序与依赖

```
Phase 0 (测试护栏)
    ↓
Phase 1 (DIP 修复: D1,D2,D3)
    ↓
Phase 2 (Wiring 统一: D4) ─────┐
    ↓                          ↓
Phase 3 (create_app 拆分: D5) ↓
    ↓                          ↓
Phase 4 (全局状态消除: D6)    ↓
    ↓                          ↓
Phase 5 (模块清理: D7) ────────┘
    ↓
Phase 6 (API 重构: 按用户旅程)
    ↓
Phase 7 (配置统一)
```

**总预计周期**：17周（约4个月）

**关键里程碑**：
- 第4周：所有 DIP 违规修复完成，domain 层完全纯净
- 第7周：Wiring 系统100% 迁移到 ServiceRegistry，4000+ 行旧 wiring 代码删除
- 第11周：全局可变状态 < 3 个（仅保留 Flask app 自身状态）
- 第16周：API 按用户旅程重组，每个路由文件 ≤ 200 行

---

## 五、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Phase 1 修改 port 接口破坏 downstream | 高 | 高 | 每个 port 先写 protocol 测试 |
| Phase 2 迁移 wiring 时遗漏某个服务依赖 | 中 | 高 | 保留旧 wiring 作为 fallback，新增 `@require` 装饰器做缺失检查 |
| Phase 4 删除全局状态后某个 helper 找不到实例 | 中 | 中 | 全局搜索 `_instance` / `_bound` 使用方 |
| Phase 6 API 重组导致前端页面 404 | 高 | 中 | 先加反向代理兼容旧路径 |
| 团队不熟悉 DDD/Port-Adapter 模式 | 中 | 中 | 先做 1-2 个文件的 demo PR，展示模式 |

---

## 六、预期收益

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| `create_app()` 行数 | 245 | < 20（调用 8 个步骤函数） |
| Wiring 代码行数 | ~5000 | ~500（声明式 `@register_service`） |
| Domain 层纯净度 | 2 处 DIP 违规 | 100% 依赖倒置 |
| Presentation 层纯净度 | 13 个文件直连 infrastructure | 0 违规 |
| Application helpers 数量 | 40+ 基础设施代理 | 5-8 个真正的 use-case helper |
| 全局可变状态 | 50+ 全局变量/单例 | < 3 |
| 测试覆盖率 | ~0% | 60%+ |
| 单路由文件最大行数 | 676 (`routes_v1_stock.py`) | 200 |
| ContextModule 声明 | 4 个 + 过程式 wiring | 4 个 + 声明式 |

---

## 七、不做什么（明确范围外）

- **不重构 AI Agent 内部逻辑**：六分析师辩论链、EvidenceBlackboard、TieredLLM 等 LangGraph 实现保持不变
- **不重构 Qlib 集成**：`infrastructure/qlib/` 和 `application/services/qlib/` 保持不变
- **不重构 Pytdx TDX 协议**：`infrastructure/pytdx/` 保持不变
- **不重构 Celery 任务**：`tasks/` 保持不变（但可以通过 Port 间接使用服务）
- **不重构前端模板**：HTML Jinja2 模板保持不变

---

## 附录 A：Phase 1 详细文件清单

### A.1 DIP 修复文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `domain/ports/timeseries_ports.py:191` | 删除导入 | 将 `fetch_questdb_ohlcv` 调用改为通过 port |
| `domain/ports/timeseries_ports.py:317` | 删除导入 | 将 `fetch_clickhouse_ohlcv` 调用改为通过 port |
| `domain/ports/timeseries_port.py` | 新建 | 纯接口 `TimeSeriesDBPort` |
| `infrastructure/timeseries/port_adapter.py` | 新建 | 实现 `TimeSeriesDBPort` |
| `presentation/api/routes_v1_agent_swarm.py` | 修改 import | 改用 port/service |
| `presentation/api/routes_v1_investment_committee.py` | 修改 import ×5 | 改用 port/service |
| `presentation/api/routes_v1_stock.py` | 修改 import | 改用 port/service |
| `presentation/web/pages_admin.py` | 修改 import | 改用 port/service |
| `presentation/api/agent_swarm/routes.py` | 修改 import ×2 | 改用 port/service |

### A.2 Application Helpers 分类

| 类别 | 文件数 | 示例 | 迁移目标 |
|------|--------|------|---------|
| 市场数据访问 | 12 | `tdx_local_access.py`, `qlib_access.py`, `market_data_provider.py` | `infrastructure/adapters/market_data/` |
| 因子/Alpha 访问 | 8 | `factor_access.py`, `rdagent_access.py`, `pytdx_access.py` | `infrastructure/adapters/alpha/` |
| 研报/新闻访问 | 4 | `news_access.py`, `report_access.py` | `infrastructure/adapters/news/` |
| 代理/网关 | 6 | `rust_indicators.py`, `tencent_gateway.py` | `infrastructure/adapters/indicators/` |
| 其他杂项 | 10 | `stock_cache.py`, `industry_map.py` | 按功能分组 |
