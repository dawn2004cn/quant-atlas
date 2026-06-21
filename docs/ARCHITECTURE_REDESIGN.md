# Flask 量化平台重构设计

## 目标

基于现有 `scripts/` 下已经沉淀的数据抓取、回测、选股能力，重构为一个可扩展、可维护、符合工程化规范的 Flask 项目。重构后的第一阶段重点是：

- 保留并复用现有 A 股能力
- 为美股、港股预留统一接口
- 将数据源、策略、仓储、控制器解耦
- 将“脚本集合”演进为“分层应用”
- 用依赖反转承接未来的 `qstock`、`qlib`、`yfinance`、`ta`、`tdx`、搜狐、腾讯等适配器

## 新目录结构

```text
quant-atlas/
├─ app/
│  ├─ application/
│  ├─ domain/
│  ├─ infrastructure/
│  ├─ presentation/
│  ├─ bootstrap.py
│  ├─ config.py
│  └─ __init__.py
├─ scripts/
├─ run.py
└─ ARCHITECTURE_REDESIGN.md
```

## 分层职责

### 表现层 `presentation`

- 只负责路由、请求参数、响应输出、页面渲染
- 不直接访问外部 API，不直接拼接业务规则

### 应用层 `application`

- 组织用例
- 编排领域端口
- 不关心底层是 JSON、Redis、SQLite、腾讯、TDX 还是 qstock

### 领域层 `domain`

- 定义核心模型和抽象端口
- 这里不依赖 Flask、akshare、旧脚本

### 基础设施层 `infrastructure`

- 负责实现端口
- 负责对接旧脚本与第三方数据源

## 功能映射

- A 股市场全景图: `/api/markets/CN/panorama`
- 美股全景图预留: `/api/markets/US/panorama`
- 港股全景图预留: `/api/markets/HK/panorama`
- 全市场实时数据: `/api/markets/CN/quotes`
- 个股详情: `/api/stocks/CN/<symbol>`
- 历史数据与指标: `/api/stocks/CN/<symbol>/history`
- 中长线策略选股: `/api/strategies/select`
- 回测: `POST /api/strategies/backtest`
- 自选股管理: `/api/watchlist`
- 用户管理: `/api/users`

## 六大原则落地

- 单一职责: 路由、应用服务、Provider、Repository 各司其职
- 开闭原则: 新增数据源实现端口即可扩展
- 里氏替换: 任意 Provider 都可替换旧脚本适配器
- 接口隔离: 市场、新闻、指标、回测、仓储分别建口
- 依赖倒置: 应用层只依赖抽象端口
- 迪米特法则: 控制器不感知底层脚本细节

## 建议的下一步

- 把用户与自选股从 JSON 升级到数据库
- 将前端模板接口切换到新的 `/api/*`
- 为美股、港股补充 `yfinance` / `qstock` 适配器
- 为 `qlib` 增加因子研究与回测增强能力

## 端到端目标与闭环流程

产品级目标、能力矩阵、数据一致性规范及 **Phase A–D** 路线图见 **[case.md](case.md)**（与当前 Flask/Celery/Qlib/RD-Agent 实现对齐）。架构上仍坚持本页分层：**研究编排走应用服务，数据写入走基础设施，表现层不直连源站**。

## Current Status

- Active backend entrypoint: `run.py`
- Active app factory: `app/bootstrap.py`
- Active JSON API namespace: `/api/v1/*`
- Users, watchlist, and stock groups are now stored in SQLite
- Legacy transition reference: `LEGACY_STATUS.md`
- `scripts/` / `stock-analysis/` / `TradingAgents-CN-lastest` 与主平台的对照与迁移状态: [scripts_inventory.md](scripts_inventory.md)
- 数据本地优先与定时策略: [DATA_FLOW.md](DATA_FLOW.md)
