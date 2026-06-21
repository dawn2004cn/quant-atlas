# scripts 迁移计划

## 目标

`scripts/` 当前仍然是混合目录。为了避免继续堆积历史脚本，后续迁移按下面的目标结构推进：

- `scripts/ops/`
  面向运维与巡检，保留少量人工执行的辅助脚本。
- `scripts/migrations/`
  面向一次性或低频迁移任务，如数据库迁移、缓存迁移。
- `scripts/experiments/`
  面向策略实验、数据源试验、一次性研究脚本。
- `scripts/candidates/`
  面向暂时不进入主平台链路、但需要先集中管理的候选脚本。

长期目标不是把所有脚本都保留下来，而是：

- 生产链路迁入 `app/tasks/` 或 `app/application/services/`
- 通用 CLI 迁入 `app.cli`
- 只保留确有价值的运维与实验脚本

## 批次建议

### 第一批：直接归位到分类目录

优先处理那些职责最清晰、与主平台耦合较低的脚本。

- `migrate_sqlite_to_mysql.py`
- `migrate_sqlite_to_redis.py`
- `migrate_investment_managers_sqlite_to_mysql.py`
- `sync_sqlite_to_redis.py`
- `check_cache.py`
- `check_movements.py`
- `verify_backend.py`
- `verify_logic.py`

建议动作：

- 迁移到 `scripts/migrations/` 或 `scripts/ops/`
- 在文件头补充用途、输入和执行前提

### 第二批：生产链路候选，先归拢到 candidates

这类脚本如果仍在使用，先不直接迁入主平台，而是集中到 `scripts/candidates/`。

- `update_all_market_data.py`
- `update_daily_latest.py`
- `schedule_history_update.py`
- `refresh_stock_history_cache.py`
- `warmup_market_cache.py`
- `stock_async_fetcher.py`
- `update_stock_history_to_cache.py`
- `update_stock_history_to_csv.py`

建议动作：

- 先迁移到 `scripts/candidates/`
- 根目录保留兼容包装入口
- 后续再根据使用频率决定是否迁入 `app.cli` / `app.tasks`

### 第三批：策略与实验脚本

这类脚本需要先做价值判断，再决定迁入还是归档。

- `long_term_selector.py`
- `short_term_selector.py`
- `quant_screener.py`
- `tau_selector.py`
- `bollinger_rsi_selector.py`
- `ema_macd_selector.py`
- `stochastic_selector.py`
- `volume_breakout_selector.py`
- `ml_trading_bot.py`
- `stock_financial_analysis.py`

建议动作：

- 有复用价值的，提炼成策略 Provider 或领域服务
- 仅供研究参考的，放入 `scripts/experiments/`
- 长期不用的，标记可归档

## 执行规则

- 不再向 `scripts/` 根目录新增长期脚本。
- 新增运维脚本时，优先放 `scripts/ops/`。
- 新增迁移脚本时，优先放 `scripts/migrations/`。
- 新增实验脚本时，优先放 `scripts/experiments/`。
- 新增长期候选脚本时，优先放 `scripts/candidates/`。
- 一旦脚本进入稳定生产主链路，再评估迁入 `app/`。

## 与现有文档的关系

- 总体边界说明见 `docs/PLATFORM_BOUNDARY.md`
- 当前脚本清单见 `docs/scripts_inventory.md`
- `scripts/README.md` 用于目录级提醒
