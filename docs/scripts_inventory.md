# 脚本与子工程清单（迁移与集成）

本文档落实「三目录」梳理结论：**`scripts/`** 做可检索清单；**`stock-analysis/`**、**`TradingAgents-CN-lastest/`** 标明与主应用关系。新功能一律写在 `app/`（见 [LEGACY_STATUS.md](LEGACY_STATUS.md)）。

**扫描范围**：`scripts/**/*.py`，排除 `scripts/.venv/`、`__pycache__`、以及文件名以 `test_` 开头的单测脚本。  
**状态图例**：

| 状态 | 含义 |
|------|------|
| **已替代** | `app/` 已有等价或严格上位实现，脚本仅作历史对照 |
| **薄封装** | 小 CLI，内部已调用 `app.*`，可保留作运维命令行入口 |
| **已集成** | 逻辑在 `app/cli`（或应用服务），`scripts/*.py` 仅为兼容入口 |
| **占位** | 入口已改为打印说明，引导使用平台 API / 页面 |
| **待评估** | 若有生产仍在使用，应迁到 `app/tasks`（Celery）或 `app/application` 并补测；否则可归档 |
| **归档参考** | 旧单体/第二套架构，不建议再扩展 |

---

## 1. `scripts/` 根目录与一级子目录

| 路径 | 用途摘要 | 状态 | 平台替代或备注 |
|------|----------|------|----------------|
| `web_app.py` | 旧单体 Flask + 蓝图 | **归档参考** | `run.py` + `app/bootstrap.py` |
| `config.py` | 旧脚本侧配置 | **已替代** | `app/config.py` + `AppSettings.from_env()` |
| `stock_cache_db.py` | 旧 SQLite 缓存 | **已替代** | `app/infrastructure/database/stock_cache_db.py` |
| `cache_factory.py` / `redis_cache.py` | 缓存工厂与 Redis | **已替代** | 平台行情/任务以应用服务 + Redis（Celery/消息）为准 |
| `backtest_engine.py` / `trading_strategies.py` / `strategy_engine.py` | 旧回测与策略基类 | **已替代** | `app/services/backtest/`、`DefaultStrategyProvider` / `StrategyToolBridge` |
| `interfaces/*.py` | 旧接口抽象 | **归档参考** | `app/domain/ports` + infrastructure 实现 |
| `services/*.py` + `service_container.py` | 旧服务容器 | **归档参考** | `app/bootstrap.py` 依赖注入 |
| `data_fetchers.py` / `enhanced_data_fetcher.py` / `hybrid_data_source.py` / `smart_data_source.py` | 多源抓取与融合 | **已替代** | `MultiSourceMarketProvider`、`MarketDataAccess` |
| `realtime_reader.py` / `sina_realtime_reader.py` / `eastmoney_realtime_reader.py` | 实时行情读取 | **已替代** | `app/infrastructure/providers/market_data.py` 等 |
| `market_sentiment.py` | 市场情绪 | **已替代** | `MarketApplicationService.get_sentiment` + API |
| `fundamental_data.py` / `fundamental_data_reader.py` | 基本面 | **已替代** | `CnAkShareFundamentalsProvider`、`FundamentalDataAccess` |
| `longhubang.py` | 龙虎榜入库 CLI | **已集成** | 委托 `python -m app.cli longhu` → `BasicMarketDataService.ingest_longhu_em` |
| `yanbao.py` | 研报入库 CLI | **已集成** | 委托 `python -m app.cli yanbao` → `ingest_yanbao_eastmoney_html` |
| `eastmoney_news.py` | 东财滚动新闻 CLI | **已集成** | 委托 `python -m app.cli portal-eastmoney`；实现见 `app/cli/portal_news.py` |
| `tonghuashun_news.py` | 同花顺股道新闻 CLI | **已集成** | 委托 `python -m app.cli portal-10jqka` |
| `long_term_selector.py` / `enhanced_long_term_selector.py` / `long_term_strategies.py` | 中长线选股 | **待评估** | 与 `SelectionSourceService`、策略服务重叠；有独特因子再迁入 |
| `short_term_selector.py` / `short_term_indicators.py` / `short_term_strategies.py` | 短线选股 | **待评估** | 同上 |
| `tau_selector.py` / `stochastic_selector.py` / `volume_breakout_selector.py` / `dualma_selector.py` / `ema_macd_selector.py` / `bollinger_rsi_selector.py` / `quant_screener.py` | 各类筛选器 | **待评估** | 可合并为策略 Provider 条目 |
| `base_selection_model.py` / `advanced_long_term_indicators.py` / `advanced_indicators.py` / `tech_indicators.py` | 指标与选股基类 | **待评估** | 与 `TaIndicatorProvider` 对照后决定去留 |
| `tdx_connect_manager.py` / `tdx_config_reader.py` / `tdx_servers_connect.py` / `tdx_realtime_reader.py` / `tdx_local_data_reader.py` / `tdx_finance_reader.py` | 通达信连接与读盘 | **已部分替代** | `app/infrastructure/tdx_local/`；独有连接策略再抽 |
| `tdx_quant_screener.py` / `tdx_poolandformula_screener.py` | 通达信板块/公式扫描 | **待评估** | 与 `PoolApplicationService`、板块工具对照 |
| `candidates/update_all_market_data.py` / `candidates/update_daily_latest.py` / `candidates/schedule_history_update.py` / `candidates/refresh_stock_history_cache.py` / `candidates/warmup_market_cache.py` / `candidates/stock_async_fetcher.py` / `candidates/update_stock_history_to_cache.py` / `candidates/update_stock_history_to_csv.py` | 候选脚本（第二批已归位） | **薄封装** | 新位置以 `scripts/candidates/` 为准，根目录保留兼容包装 |
| `update_market_all_cache_from_history.py` / `download_a_shares_resume.py` | 历史/全量更新 | **待评估** | 暂未归位到候选目录，后续继续判断 |
| `initialize_data.py` / `import_stock_data.py` / `import_history_to_redis.py` | 缓存/迁移/导入 | **待评估** | 一次性迁移脚本；确认无生产依赖后可标归档 |
| `migrations/migrate_sqlite_to_mysql.py` / `migrations/migrate_investment_managers_sqlite_to_mysql.py` / `migrations/migrate_sqlite_to_redis.py` / `migrations/sync_sqlite_to_redis.py` | 迁移脚本（第一批已归位） | **薄封装** | 新位置以 `scripts/migrations/` 为准，根目录保留兼容包装 |
| `check_encoding.py` / `check_file.py` / `check_self_stocks.py` / `check_zixuang.py` | 本地检查脚本 | **待评估** | 可改为 `pytest` 或运维 CLI |
| `ops/check_cache.py` / `ops/check_movements.py` / `ops/verify_backend.py` / `ops/verify_logic.py` | 运维/检查脚本（第一批已归位） | **薄封装** | 新位置以 `scripts/ops/` 为准，根目录保留兼容包装 |
| `fix_encoding.py` / `fix_specific_files.py` | 修复脚本 | **归档参考** | 一次性维护用 |
| `_check_qlib.py` | Qlib 环境检查 | **薄封装/待评估** | 可与 `tests/test_qlib_pipeline.py` 合并 |
| `smart_market_updater.py` / `is_trading_time.py` | 市场更新与时间 | **待评估** | 与扫描器、交易历对照 |
| `ml_trading_bot.py` / `stock_financial_analysis.py` | ML/财务分析实验 | **待评估** | 非核心路径；迁入需单独模块与依赖声明 |
| `utils.py` | 旧公共工具 | **待评估** | 被 `backtest_engine` 等引用；随旧引擎归档 |

**异常/冗余文件名**（建议勿再依赖）：

- `scripts/update_stock_history_to_csv - 副本.py`：**归档参考**，应删除或合并到 `update_stock_history_to_csv.py`（若仍需）。

---

## 2. `stock-analysis/`（独立子工程）

| 说明 | 与平台关系 |
|------|------------|
| 通达信本地 → CSV/pickle、财务、`xuangu`/策略模板、rqalpha 回测等 | **`app/infrastructure/tdx_local/`** 与 **`quant_tools.get_tdx_local_snapshot`** 已对齐同类数据源思路 |
| **集成策略** | **不整目录并入 `app/`**；若前复权/财务字段与线上一致性更好，**单函数 + 单测**迁入 `tdx_local`；选股逻辑有验证价值则迁入 **策略 Provider** |

详见子目录内 `README.md`（上游 wkingnet / Gitee 文档为主）。

---

## 3. `TradingAgents-CN-lastest/`（上游参考工程）

| 说明 | 与平台关系 |
|------|------------|
| 含专有许可分段、`web/`、`tradingagents/` 全栈 | 本仓库 **`app/agents/research/`** 为**自研 LangGraph**，**不依赖**该目录 Python 包 |
| 新闻过滤、基本面等思路 | 已部分吸收：`app/services/news/`、`cn_akshare_fundamentals` 等 |
| **集成策略** | **作岛外参考**；排错时 diff；适配器 cherry-pick 时注意 **LICENSE/COPYRIGHT**；勿整树合并进发布产物 |

---

## 4. 统一 CLI（占位 / 薄封装已并入）

自仓库根目录：

```bash
python -m app.cli --help
python -m app.cli portal-eastmoney [--out-dir DIR] [--limit N]
python -m app.cli portal-10jqka [--out-dir DIR] [--limit N]
python -m app.cli longhu [--lookback-days 14]
python -m app.cli yanbao
```

`scripts/longhubang.py`、`scripts/yanbao.py`、`scripts/eastmoney_news.py`、`scripts/tonghuashun_news.py` 为兼容薄壳，内部调用上述子命令。

---

## 5. 维护约定（摘要）

1. **新代码**：只加在 `app/`（表现层 / 应用服务 / 领域 / 基础设施）。  
2. **仍要跑的批处理**：迁入 `app/tasks/` 或文档化 CLI，配置走 `AppSettings`/环境变量。  
3. **本表更新**：删除或迁移某脚本时，在本表对应行更新「状态」并注明 PR/日期。  
4. **单测**：以仓库根 `tests/` 为准；`scripts/test_*.py` 不纳入本表、逐步淘汰重复项。

---

## 6. 相关文档

- [LEGACY_STATUS.md](LEGACY_STATUS.md) — 废弃入口与存储现状  
- [QUANT_ATLAS_平台手册.md](QUANT_ATLAS_平台手册.md) — 主架构与目录  
- [ARCHITECTURE_REDESIGN.md](ARCHITECTURE_REDESIGN.md) — 分层原则
