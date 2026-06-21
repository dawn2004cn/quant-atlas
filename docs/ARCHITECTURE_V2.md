# Quant Atlas 系统架构文档

**版本**: 2.0  
**日期**: 2026-04-27  
**状态**: 生产级

---

## 1. 架构总览

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│  (Web UI, API, Templates)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Application Layer                    │
│  (Services, Workflows, DTOs)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Domain Layer                      │
│  (Entities, Contracts, Events, Alpha, Execution)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                 │
│  (Repositories, Providers, Persistence, Compute) │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块

### 2.1 Domain Layer (`app/domain/`)

| 模块 | 职责 | 核心类 |
|------|------|--------|
| `contract/` | 统一契约 | `AlphaEntity`, `Signal` |
| `alpha/` | Alpha因子工厂 | `WorldQuantKnowledge`, `FactorVault`, `Autopilot` |
| `execution/` | 实盘执行 | `DigitalTwin`, `HighFidelityExecutor` |
| `events_core` | 领域事件 | `DomainEvent`, `EventDispatcher` |
| `ports/` | 端口接口 | `TaskDispatcher`, `FactorVaultStorage` |

#### Alpha Factory 核心组件

```python
from app.domain.contract import AlphaEntity, AlphaSource, AlphaStatus
from app.domain.alpha import (
    WorldQuantKnowledge,      # 20个经典Alpha + 28算子
    get_factor_vault,          # 因子持久化
    get_autopilot,           # 自主驾驶控制器
    get_production_research_bridge,  # 研发-实盘桥梁
)
```

### 2.2 Application Layer (`app/application/`)

| 模块 | 职责 |
|------|------|
| `workflow/` | 自主Pipeline |
| `services/` | RDAgent/Celery集成 |
| `dto/` | 数据传输对象 |

#### 自主驾驶流程

```python
from app.application.workflow import get_autopilot, AutopilotConfig

ap = get_autopilot(AutopilotConfig(drift_threshold=0.15))
report = ap.check_drift("strategy_a", backtest_return=0.20, live_return=0.05)
# 5步: Drift检测 → 根因 → RD-Agent → 影子测试 → 热切换
```

### 2.3 Infrastructure Layer (`app/infrastructure/`)

| 模块 | 职责 |
|------|------|
| `persistence/` | Redis知识图谱 |
| `compute/` | Numba向量化计算 |
| `memory/` | Arrow共享内存 |
| `repositories/` | `common/` · `mysql/` · `sqlite/` · `postgres/`（见 `docs/refactor/repositories-layout.md`） |
| `database/` | MySQL / PostgreSQL 连接、ORM models |
| `providers/` | TDX/AKShare数据 |

#### 知识图谱

```python
from app.infrastructure.persistence import get_knowledge_store

store = get_knowledge_store()
store.store_experiment(ExperimentRecord(...))
store.query_historical_context("600519", "momentum_insensitive")
```

### 2.4 Agents Layer (`app/agents/`)

| 模块 | 职责 |
|------|------|
| `research/graph.py` | 6分析师LangGraph |
| `evidence_blackboard` | 结构化证据 |
| `hierarchical_teams` | 层级并行 |
| `tiered_llm` | 成本优化 |

#### Agent集成

```python
from app.agents.research.graph import build_custom_trading_graph
from app.agents.evidence_blackboard import get_evidence_blackboard

# Evidence驱动的早停逻辑
```

---

## 3. 数据流

### 3.1 Alpha研发流程

```
RD-Agent → qlib_backtest → AlphaEntity → FactorVault
         ↓
    KnowledgeStore (Redis)
         ↓
    ProductionResearchBridge
         ↓
    DigitalTwin (双路执行)
         ↓
    热切换部署
```

### 3.2 Agent决策流程

```
Supervisor
  ├─ Macro Analyst
  ├─ Fundamental Analyst
  ├─ Technical Analyst
  ├─ Sentiment Analyst
  └─ Backtest Optimizer
        ↓
  [EvidenceBlackboard] ← 结构化存储
        ↓
  EvidenceRouter ← 早停逻辑
        ↓
  Risk Manager → Final Verdict
```

---

## 4. 关键接口

### 4.1 AlphaEntity

```python
@dataclass
class AlphaEntity:
    id: str
    formula: str
    source: AlphaSource       # RD_AGENT, TECHNICAL_ANALYST, MANUAL
    status: AlphaStatus      # EXPERIMENT → BACKTEST → PRODUCTION
    metrics: AlphaMetrics   # IC, IR, Sharpe
    
    def is_production_ready(self) -> bool:
        return self.status in [VALIDATION, PRODUCTION] and self.metrics.ir > 0.5
```

### 4.2 Signal

```python
@dataclass
class Signal:
    id: str
    symbol: str
    signal_type: SignalType   # LONG, SHORT, NEUTRAL
    strength: SignalStrength
    alpha_id: str | None
    confidence: float
```

### 4.3 AutopilotConfig

```python
@dataclass
class AutopilotConfig:
    drift_threshold: float = 0.15      # 15% 漂移阈值
    shadow_test_duration_hours: int = 48
    auto_deploy_enabled: bool = False
    regime_switch_enabled: bool = True
```

---

## 5. 配置管理

### 5.1 环境变量

```bash
# .env
REDIS_URL=redis://localhost:6379
QLIB_DATA_DIR=instance/qlib_bin
TDX_ROOT_PATH=C:/new_tdx
CELERY_BROKER=redis://localhost:6379/0
```

### 5.2 端口定义

```python
# app/domain/ports/task_ports.py
class TaskDispatcher(ABC):
    @abstractmethod
    def dispatch(self, func, task_name: str, args: list): ...

# app/domain/ports/factor_ports.py  
class FactorVaultStorage(ABC):
    @abstractmethod
    def save(self, alpha: AlphaEntity): ...
    @abstractmethod
    def get(self, alpha_id: str) -> AlphaEntity: ...
```

---

## 6. 部署架构

```text
┌─────────────┐     ┌─────────────┐
│   Web UI    │     │  RD-Agent  │
│  (Flask)   │     │  (Celery)  │
└──────┬──────┘     └─────┬─────┘
       │                 │
       ▼                 ▼
┌─────────────────────────────────┐
│      Application Layer            │
│  (Services, Workflows)        │
└───────���──────┬───────────────┘
              │
              ▼
┌─────────────────────────────────┐
│       Domain Layer              │
│  (Alpha, Contracts, Events)    │
└──────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────────┐
│    Infrastructure              │
│  MySQL | Redis | qlib | TDX    │
└─────────────────────────────────┘
```

---

## 7. API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/alpha-factory/status` | GET | Autopilot状态 |
| `/api/v1/rd-agent/runs` | POST | 提交实验 |
| `/api/v1/factors` | GET | 因子列表 |
| `/api/v1/backtest` | POST | 回测 |
| `/api/v1/signal-flag/pool` | GET/POST | 信号旗池 |
| `/api/v1/signal-flag/observations` | GET | 信号观察追踪 |
| `/api/v1/investment-manager/simulate` | POST | 投资经理模拟 |
| `/api/v1/investment-manager/replay` | POST | 历史信号回放 |
| `/api/v1/moments/feed` | GET | 投资时刻动态 |
| `/api/v1/moments/post` | POST | 发布投资时刻 |
| `/api/v1/moments/agent-reply` | POST | AI智能回复 |
| `/api/v1/ai-hedge-fund/analysis` | POST | AI对冲基金分析 |
| `/api/v1/ai-hedge-fund/report` | GET | 研报解读 |
| `/api/v1/fingpt/analyze` | POST | FinGPT分析 |
| `/api/v1/qlib/convert` | POST | 数据转换为Qlib格式 |
| `/api/v1/risk/portfolio` | GET | 组合风险敞口 |
| `/api/v1/risk/alert` | POST | 设置风险告警 |
| `/api/v1/factor/orthogonalize` | POST | 因子正交化 |
| `/api/v1/factor/self-correction` | POST | 因子自校正 |
| `/api/v1/factor/ic-monitor` | GET | IC监控状态 |
| `/api/v1/task-pipeline/dag` | GET/POST | DAG任务编排 |
| `/api/v1/task-pipeline/status` | GET | 任务执行状态 |
| `/api/v1/data-infrastructure/quality` | GET | 数据质量报告 |
| `/api/v1/data-infrastructure/backfill` | POST | 数据回填 |
| `/api/v1/user/lifecycle` | GET/POST | 用户生命周期 |
| `/api/v1/user/profile` | GET/PUT | 投资画像 |
| `/api/v1/user/access-policy` | GET/PUT | 访问策略 |
| `/api/v1/user/audit-trail` | GET | 操作审计日志 |
| `/api/v1/recommendation/daily` | GET | 每日推荐 |
| `/api/v1/recommendation/strategy` | GET | 策略推荐 |
| `/api/v1/industry-chain/graph` | GET | 产业链图谱 |
| `/api/v1/diagnosis/stock` | GET | 股票诊断报告 |
| `/api/v1/market/pulse` | GET | 市场脉搏 |
| `/api/v1/committee/ai-debate` | POST | AI委员会辩论 |
| `/api/v1/trade-plan/create` | POST | 交易计划 |
| `/api/v1/daily-workbench/data` | GET | 每日工作台数据 |
| `/api/v1/watchlist/agent` | POST | 观察列表智能体 |
| `/api/v1/portfolio/positions` | GET | 持仓管理 |
| `/api/v1/portfolio/history` | GET | 历史交易记录 |

---

## 8. 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/test_rdagent_artifact_registry.py -v

# 运行集成测试
pytest tests/test_app_bootstrap.py -v
```

---

## 9. 启动流程

```bash
# 开发模式
python run.py

# 生产模式
celery -A app.celery_app worker -l info
celery -A app.celery_app beat -l info
```

---

## 10. 监控指标

| 指标 | 描述 |
|------|------|
| `autopilot.state` | idle/monitoring/researching/deploying |
| `autopilot.current_regime` | bull_strong/bear_weak/ranging |
| `drift.detected` | 漂移百分比 |
| `factor.ir` | Information Ratio |
| `factor.sharpe` | Sharpe Ratio |
| `shadow.pnl` | 影子PnL vs 实盘PnL |

## 8. 新增重构增强（2026-06 Phases A-H）

### 8.1 用户旅程路由（Phase A）
- 6 个旅程：discovery / research / execution / review / monitor / manage
- 端点：`GET /api/v1/journeys`、`/journeys/{name}`、`/journeys/{name}/routes`
- 原始 325 路由零破坏，journeys 只是新 namespace

### 8.2 工作流中枢（Phase B）
- 领域模型：`domain/workflow_hub/models.py` + `ports.py`
- 线程安全存储：`infrastructure/workflow_hub/memory_repository.py`
- 工厂：`infrastructure/workflow_hub/factory.py`

### 8.3 用户上下文引擎（Phase C）
- 端点：`/user/context/{dashboard,quick-actions,suggestions}`
- 核心：`application/services/user_context_engine.py` + `default_adapter.py`

### 8.4 权限与业务条款（Phase D）
- `Capability(StrEnum)` + Free / Pro / Admin 策略
- `@requires_capability(Capability.X)` 装饰器

### 8.5 决策可追溯性闭环（Phase E）
- `@with_provenance(subject_factory, model_version)` 自动附加 provenance 摘要
- 测试：`tests/test_phase_e_provenance.py`

### 8.6 统一异常自愈（Phase F）
- `SelfHealingDomainError` + `X-QC-Degraded` 降级响应头
- 测试：`tests/test_phase_f_degraded_response.py`

### 8.7 服务分组（Phase G）
- `services/{trading,research,system,ai,analytics,user,...}/` Facade 目录就位
- 注册器：`application/services/__init__.py` → `ServiceGroupFacadeRegistry`

### 8.8 Celery 生命周期桥接（Phase H）
- `app/celery_app.py` 信号自动创建 / 完成 / 失败 workflow 实例
- 无外部接口变化，纯内部 try/except 桥接

### 9. 意图驱动与协同发现（Phase 9）

#### 9.1 意图分解器 (IntentDecomposer)
- 领域模型：`domain/intent_decomposer.py`（`ExecutionPlan` + `ExecutionStep`）
- 服务：`application/services/intent_decomposer.py`（3 种意图模板）
- 集成：`CommandPlanService.decompose_to_plan()` 扩展

#### 9.2 协同 Alpha 实验室 (Alpha-Lab)
- 元数据标准：`domain/alpha/alpha_metadata_standard.py`
  - `FactorExpression` / `FactorComposition` / `AlphaNote`
  - `AlphaNote.to_evidence_note()` → Blackboard 兼容

#### 9.3 递归式逻辑自检
- `EnhancedMarketService.cross_validate_indicators()` 并行验证指标
- fallback 实现：domain service vs numpy/pandas 简单计算对比

### 10. 前端现代化基石（Phase 10）

| 基础设施 | 文件 | 职责 |
|----------|------|------|
| 统一 API Client | `static/js/api_client.js` | fetch 封装 + 认证头 + 错误标准化 |
| 全局状态总线 | `static/js/state_bus.js` | CustomEvent + localStorage 事件状态 |
| 图表服务抽象 | `static/js/chart_service.js` | Lightweight/ECharts/Three/Flow 统一接口 |
| Focus Bar 组件 | `static/js/components/qa-focus-bar.js` | Web Component 渐进迁移 |
| 模板集成 | `base.html` | 5 个新 script 标签，零破坏 |

---## 附录: 依赖版本

```
flask>=2.3
langgraph>=0.0.20
sqlalchemy>=2.0
numpy>=1.24
pandas>=2.0
redis>=4.5
celery>=5.3
```

---

**文档状态**: 完整  
**维护者**: Quant Atlas Team