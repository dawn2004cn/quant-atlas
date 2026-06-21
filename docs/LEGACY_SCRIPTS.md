# 遗留脚本与迁移状态

> 来源：scripts_inventory.md, SCRIPTS_MIGRATION_PLAN.md, LEGACY_STATUS.md, PLATFORM_BOUNDARY.md

## 主平台与历史脚本边界

### 当前主平台
- 启动入口：`run.py`
- 主应用包：`app/`
- 运行配置：`app/config.py` 与 `config/`
- 运行时数据：`instance/`
- 正式测试：`tests/`
- 平台文档：`docs/`

日常开发、问题排查、功能扩展，应优先围绕以上目录进行。

### `scripts/` 的定位
`scripts/` 不再视为主应用的一部分，而是混合目录，主要包含三类内容：
1. **历史遗留脚本**：早期原型或旧入口，帮助理解项目演进
2. **运维与迁移工具**：数据初始化、缓存处理、数据库迁移、补数、巡检等
3. **实验性脚本**：策略验证、数据源试验、一次性分析与临时测试

### 团队约定
- 新功能默认落在 `app/` 与 `tests/`，而不是 `scripts/`
- 新的生产链路脚本需要在文档中声明用途、调用方式和是否仍被调度系统依赖
- 若某个 `scripts/` 脚本仍是生产必需，应逐步迁入 `app/tasks/`、`app/application/services/` 或明确的运维目录
- 文档和讨论中提到"系统入口"时，默认指 `run.py` 与 `app/`

## 脚本迁移状态总览

### 状态图例

| 状态 | 含义 |
|------|------|
| **已替代** | `app/` 已有等价或严格上位实现，脚本仅作历史对照 |
| **薄封装** | 小 CLI，内部已调用 `app.*`，可保留作运维命令行入口 |
| **已集成** | 逻辑在 `app/cli`（或应用服务），`scripts/*.py` 仅为兼容入口 |
| **占位** | 入口已改为打印说明，引导使用平台 API / 页面 |
| **待评估** | 若有生产仍在使用，应迁到 `app/tasks`（Celery）或 `app/application` 并补测 |
| **归档参考** | 旧单体/第二套架构，不建议再扩展 |

### 核心脚本状态

| 路径 | 用途摘要 | 状态 | 平台替代或备注 |
|------|----------|------|----------------|
| `web_app.py` | 旧单体 Flask + 蓝图 | 归档参考 | `run.py` + `app/bootstrap.py` |
| `config.py` | 旧脚本侧配置 | 已替代 | `app/config.py` + `AppSettings.from_env()` |
| `stock_cache_db.py` | 旧 SQLite 缓存 | 已替代 | `app/infrastructure/database/` |
| `cache_factory.py` / `redis_cache.py` | 缓存工厂与 Redis | 已替代 | 平台行情/任务以应用服务 + Redis 为准 |
| `backtest_engine.py` / `trading_strategies.py` | 旧回测与策略基类 | 已替代 | `app/services/backtest/` |
| `interfaces/*.py` | 旧接口抽象 | 归档参考 | `app/domain/ports` + infrastructure 实现 |
| `services/*.py` + `service_container.py` | 旧服务容器 | 归档参考 | `app/bootstrap.py` 依赖注入 |
| `data_fetchers.py` / `enhanced_data_fetcher.py` | 多源抓取与融合 | 已替代 | `MultiSourceMarketProvider`、`MarketDataAccess` |
| `realtime_reader.py` / `sina_realtime_reader.py` | 实时行情读取 | 已替代 | `app/infrastructure/providers/market_data.py` |
| `market_sentiment.py` | 市场情绪 | 已替代 | `MarketApplicationService.get_sentiment` |
| `fundamental_data.py` | 基本面 | 已替代 | `CnAkShareFundamentalsProvider` |
| `longhubang.py` | 龙虎榜入库 CLI | 已集成 | `python -m app.cli longhu` → `BasicMarketDataService.ingest_longhu_em` |
| `yanbao.py` | 研报入库 CLI | 已集成 | `ingest_yanbao_eastmoney_html` |
| `eastmoney_news.py` | 东电滚动新闻 CLI | 已集成 | `python -m app.cli portal-eastmoney` |
| `tonghuashun_news.py` | 同花顺股道新闻 CLI | 已集成 | `python -m app.cli portal-10jqka` |
| `long_term_selector.py` | 中长线选股 | 待评估 | 与 `SelectionSourceService`、策略服务重叠 |
| `short_term_selector.py` | 短线选股 | 待评估 | 同上 |
| `tau_selector.py` 等筛选器 | 各类筛选器 | 待评估 | 可合并为策略 Provider 条目 |

## 迁移计划

### 目标结构
- `scripts/ops/` — 面向运维与巡检，保留少量人工执行的辅助脚本
- `scripts/migrations/` — 面向一次性或低频迁移任务
- `scripts/experiments/` — 面向策略实验、数据源试验
- `scripts/candidates/` — 暂时不进入主平台链路但需集中管理的候选脚本

### 长期目标
- 生产链路迁入 `app/tasks/` 或 `app/application/services/`
- 通用 CLI 迁入 `app.cli`
- 只保留确有价值的运维与实验脚本

### 第一批：直接归位
优先处理职责最清晰的脚本：
- 迁移到 `scripts/migrations/` 或 `scripts/ops/`：`migrate_sqlite_to_mysql.py`, `sync_sqlite_to_redis.py`, `check_cache.py` 等
- 补充文件头：用途、输入和执行前提

### 子项目说明

**`stock-analysis/`** — 独立分析脚本子树（通达信读写等），部署主站时可按需忽略或单独阅读其 README。

**`TradingAgents-CN-lastest/`** — 可选子项目/参考实现，有独立 Docker 说明。主站部署时可按需忽略。

---
*文档生成基于当前仓库代码结构整理；如有出入以源码为准。*
