# 回测引擎配置（Quant Atlas）

回测相关环境变量与 `config.cfg` 键，与 `app/infrastructure/agent/backtest/` 实现一致。

## 费率（A 股）

| 键 | 默认 | 说明 |
|----|------|------|
| `BT_STAMP_DUTY` | `0.00025` | 卖出印花税（万 2.5，2024-10 起） |
| `BT_TRANSFER_FEE` | `0.00002` | 过户费（双边，万 2） |
| `BT_COMMISSION_RATE` | `0.00025` | 佣金费率 |
| `BT_COMMISSION_MIN` | `5` | 最低佣金（元） |

历史印花税由 `cn_stamp_tax_rate_for_date()` 按交易日自动分段；若 `config.cfg` 仍写 `BT_STAMP_DUTY=0.001`，会覆盖新默认，建议改为 `0.00025` 或删除该项。

## 滑点

| 键 | 默认 | 说明 |
|----|------|------|
| 引擎 `slippage` | `0.001` | A 股比例滑点（`ChinaAEngine`） |

A 股已启用 **tick-aware** 滑点：实际冲击 = `max(价格 × slippage, 最小变动价位)`，主板 ≥1 元股票 tick 为 **0.01 元**。

## 数据与复权

| 键 | 默认 | 说明 |
|----|------|------|
| `AKSHARE_BACKTEST_ADJUST` | `hfq` | AkShare 回测复权：`hfq` / `qfq` / `none` |

## Sharpe 无风险利率

| 键 | 默认 | 说明 |
|----|------|------|
| `BT_RISK_FREE_SOURCE` | `auto` | `auto` \| `fixed` \| `none` |
| `BT_RISK_FREE_ANNUAL` | （空） | 年化无风险利率小数，如 `0.025` = 2.5% |

- **auto**：未显式设置 `BT_RISK_FREE_ANNUAL` 时，尝试 AkShare `bond_china_yield` 取 10 年期国债收益率
- **fixed**：始终使用 `BT_RISK_FREE_ANNUAL`
- **none**：无风险利率为 0

## 指标约定

| 字段 | 含义 |
|------|------|
| `max_drawdown` | 负小数（如 `-0.08`） |
| `max_drawdown_pct` | 正百分数（如 `8.0`），前端展示为 `-8.00%` |

## 相关 API

| 端点 | 用途 |
|------|------|
| `POST /api/v1/backtest` | 经典页单策略回测 |
| `POST /api/v2/strategies/backtest` | SPA 回测 |
| `POST /api/v2/strategies/backtest/compare` | 多策略对决 |
| `POST /api/v1/nl-strategy/preview` | 自然语言策略预览回测 |
| `POST /api/v1/strategies/backtest/compare` | 多策略对比（经典页 `strategy_compare.html`） |
| `GET /api/v1/mlflow/runs` | 回测历史（`run_history.html`，需 MLflow） |

### 策略对比页 URL 参数

`strategy_compare.html?symbol=600519&strategies=MA,RSI,MACD&start=2024-01-01&end=2024-12-31`
