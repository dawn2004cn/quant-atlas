# `app` 包架构说明

本目录为 **Quant Atlas** 主程序代码根。目标：**分层清晰、依赖单向、命名可读**，并与经典 **SOLID** 原则对齐。

## 分层（自上而下依赖）

| 层级 | 路径 | 职责 | 允许依赖 |
|------|------|------|-----------|
| **表现层** | `presentation/web`、`presentation/api`、`presentation/routes` | HTTP、模板、JSON、路由注册、Flask-Login 会话模型 | `application`、`domain`、`config`；不直接写业务规则 |
| **应用层** | `application/services` | 用例编排、事务边界、权限与校验入口 | `domain`（实体/端口/枚举）；通过 **端口** 调用基础设施 |
| **领域层** | `domain` | 实体、值对象、枚举、`ports` 抽象接口、角色目录、分析逻辑 | 仅标准库 / typing；**不**依赖 `infrastructure` / `presentation` |
| **基础设施层** | `infrastructure` | 端口实现：仓储、外部 API、TDX、Qlib、消息、适配器 | `domain`；**不**依赖 `presentation` |
| **横切** | `core`、`config` | 日志、工厂、配置、工具函数 | 按需最小依赖 |
| **任务入口** | `tasks` | Celery 任务：组合应用服务与基础设施 | 与 `bootstrap` 类似，属于**组合根** |
| **兼容/组合** | `bootstrap.py`、`__init__.py` | 组装依赖、注册蓝图、预热 | 可依赖各层 |

## 统一工具门面 (ToolFacadeService)

2026-04-25 重构后，**统一工具门面** `ToolFacadeService` 合并了以下功能：

- `MarketDataAccess` - 行情数据访问
- `FundamentalDataAccess` - 基本面数据访问
- `StockNewsAccess` - 新闻数据访问
- `StrategyToolBridge` - 回测/选股桥接

**新代码使用**：
```python
from app.application.services.tool_facade_service import ToolFacadeService

# 注入 market_provider, stock_service, archive, fundamental_provider, strategy_service
facade = ToolFacadeService(...)
bars, note = facade.fetch_bars("600519", MarketCode.CN)
```

**旧接口兼容**（已标记废弃）：
```python
from app.services.data import MarketDataAccess  # DeprecationWarning
```

## API 版本化策略 (2026-04-25)

| 版本 | 路径 | 特性 |
|------|------|------|
| v1 | `/api/v1/*` | 传统格式，兼容现有客户端 |
| v2 | `/api/v2/*` | DTO 验证，标准化响应 `{ok, data, meta}` |

**v2 使用示例**：
```python
from app.presentation.api.routes_v2 import create_api_v2_blueprint
from app.presentation.api.request_parsers import parse_dto
from app.application.dto import BacktestRequestDTO

# POST /api/v2/strategies/backtest
dto = parse_dto(request.get_json(), BacktestRequestDTO)
result = strategy_service.backtest(symbol=dto.symbol, ...)
```

## 目录结构

```
app/
├── application/services/
│   ├── ToolFacadeService          # 统一工具入口 (2026-04-25)
│   ├── AnalysisPredictionService # 预测验证
│   ├── DailyAnalysisApplicationService # 每日分析
│   └── ...                       # 其他应用服务
├── domain/
│   ├── ports.py                 # 端口接口 (含 ToolFacadePort)
│   ├── entities.py              # 领域实体
│   ├── analysis/               # 技术分析 (新)
│   └── ...
├── core/utils/
│   ├── news_utils.py            # 新闻相关性 (新)
│   ├── import_utils.py          # 导入解析 (新)
│   ├── datetime_utils.py        # 日期工具
│   └── pandas_utils.py          # Pandas 工具
├── infrastructure/
│   ├── repositories/           # common/ mysql/ sqlite/ postgres/ + 根 shim
│   │   └── 见 docs/refactor/repositories-layout.md
│   ├── database/               # mysql_client, postgres_client, ORM models
│   ├── adapters/               # 外部适配器
│   └── ...
├── services/                     # 兼容层 (已废弃)
├── presentation/
│   ├── web/                    # Web 页面
│   └── api/                   # REST API
└── tasks/                      # Celery 任务
```

## SOLID 对照

1. **S** 单一职责：`ToolFacadeService` 统一工具入口，`application/services` 承担用例
2. **O** 开闭：新数据源实现 `domain.ports` 中的端口，而非修改多处
3. **L** 里氏替换：端口实现须遵守抽象契约
4. **I** 接口隔离：端口按能力拆分
5. **D** 依赖倒置：应用层只依赖 `domain.ports`
6. **迪米特**：表现层只调应用服务

## 相关文档

- 仓库级手册���`docs/QUANT_ATLAS_平台手册.md`
- 重构记录：`REFACTORING_LOG.md`
- Repositories 布局：`docs/refactor/repositories-layout.md`
- 数据库配置：`docs/DATABASE_GUIDE.md`
- 根 `README.md`：快速启动与依赖