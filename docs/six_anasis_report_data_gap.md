# 数据缺口补齐方案与建议

> 基于 `six_anasis_report.md` 六角色分析报告，针对标的 **688313** 的数据缺口分析

---

## 缺口总览

| 缺口编号 | 缺口类型 | 当前状态 | 补齐方案 |
|---------|---------|---------|---------|
| A | 财务深度 | **已具备** | 确认工具可用性 |
| B | 实时动态 | **部分缺失** | 补充情绪指标/舆情分析 |
| C | 因子/回测 | **已具备** | 验证可靠性、补充缺失依赖 |

---

## A. 财务深度 — **已具备，建议激活验证**

### 现状

| 组件 | 状态 | 说明 |
|-----|-----|-----|
| `get_cn_financial_statements` | ✅ 已实现 | `quant_tools.py:1248` |
| 数据源 | ✅ AkShare EastMoney | 资产负债表 + 利润表 + 现金流量表 |
| 存储 | ✅ 已有 | `cn_financial_stash` 表 |
| 定时任务 | ✅ 已有 | Celery `scheduled_financial_stash_refresh` |

### 补齐建议

**目的：** 确认该工具在 688313 上实际能返回数据，而非空响应。

1. **直接调用验证** — 发起请求调用 `get_cn_financial_statements(stock_code="688313")`，确认返回：
   - `balance_sheet` (资产负债表)
   - `profit_sheet` (利润表)
   - `cash_flow_sheet` (现金流量表)
   - `financial_abstract` (财务摘要)

2. **若返回空数据** — 排查方向：
   - AkShare EastMoney 接口是否对该科创板股票有访问限制
   - 检查 `CnAkShareFundamentalsProvider` 的错误日志
   - 备选方案：接入 Tushare（需要 token），补充 AkShare 数据不足的部分

3. **美国/HK 股票财务数据** — 当前 AkShare 仅覆盖 A 股。若分析范围扩展至美股，需接入 `yfinance` 获取财务报表（利润表/现金流量表/资产负债表）。

---

## B. 实时动态 — **部分缺失，需补充两项**

### 现状

| 组件 | 状态 | 说明 |
|-----|-----|-----|
| `get_stock_news` | ⚠️ 存在 | AkShare 新闻源，但日志显示失败记录 |
| `get_yanbao_market_digest` | ✅ 存在 | 研报聚合，从本地数据库读取 |
| 情绪打分/VIX 类指标 | ❌ **缺失** | 未找到市场情绪量化指标 |

### 补齐建议

#### B1. 舆情情绪量化（高优先级）

当前平台有新闻，但**缺少情绪打分**。建议实现：

- **方案 1（轻量）：** 对 `get_stock_news` 返回的新闻标题/摘要做情感分析
  - 使用 `transformers` / `snownlp` 对新闻文本进行情感打分（0-1）
  - 聚合计算近 N 天的平均情绪分
  - 输出：`avg_sentiment_score`, `positive_count`, `negative_count`, `neutral_count`

- **方案 2（中量）：** 接入东方财富股吧/雪球舆情 API
  - 部分舆情数据可通过 AkShare 获取（如 `stock_board_em_sub_contract_scr`)
  - 爬取雪球评论情感倾向

#### B2. 市场情绪仪表盘数据（中优先级）

建议新增工具函数：

```
get_market_mood_indicator(market: str) -> {
    "vix_equivalent": float,          # 类似 VIX 的波动率情绪指标
    "money_flow_level": str,          # "inflow" | "neutral" | "outflow"
    "hot_topic_count": int,           # 当日该股相关热议数量
    "sentiment_trend": [float],       # 近7天情绪趋势
    "risk_level": str                 # "low" | "medium" | "high"
}
```

数据来源：
- 涨跌幅家数比例（已有 `market_sentiment` 表）
- 板块资金净流入（需 AkShare `stock_marketCL_marketCGC`）
- 新闻/公告数量统计

---

## C. 因子/回测 — **已具备，需修复可靠性**

### 现状

| 组件 | 状态 | 说明 |
|-----|-----|-----|
| `run_backtest` | ✅ 已实现 | `quant_tools.py:538` |
| `get_qlib_factor_snapshot` | ✅ 已实现 | `quant_tools.py:670` |
| Qlib Service | ✅ 已实现 | `qlib_service.py` |
| 依赖条件 | ⚠️ 需满足 | 需 `ENABLE_QLIB=1` 且存在 `instance/qlib_bin` 数据 |

### 补齐建议

#### C1. 验证 Qlib 环境可用性（高优先级）

检查项：
1. 环境变量 `ENABLE_QLIB` 是否设置为 `1`
2. `instance/qlib_bin` 目录是否存在且包含因子数据
3. 依赖包 `qlib` 是否正确安装

若 Qlib 不可用，**降级方案**：
- 使用本地 SQLite 历史数据 + Python `pandas` 进行简单因子计算（MA、EMA、RSI、MACD）
- 优点：不依赖 Qlib，稳定性高
- 缺点：因子种类有限

#### C2. 简化回测引擎（新增轻量方案）

当前 Qlib 回测依赖较重，建议新增一个**轻量回测工具**：

```python
def simple_backtest(
    stock_code: str,
    strategy: str,        # "ma_cross" | "rsi_oversold" | "dual_thrust"
    start_date: str,
    end_date: str,
    initial_cash: float = 100000
) -> dict:
    # 返回：总收益率、年化收益率、最大回撤、夏普比率、交易次数
```

基于本地 `stock_cache.db` 历史数据和简单策略逻辑，无需 Qlib。

#### C3. 筹码分布数据（与 `get_chip_distribution` 关联）

报告中提到需要 `get_chip_distribution`，代码中**已实现**（`quant_tools.py:1574`），使用 AkShare `cyq` 数据源。

**补齐：** 确认 `get_chip_distribution(stock_code="688313")` 在目标股票上实际能返回数据，并返回给前端展示。

---

## 实施优先级

```
P0 (立即)
├── 1. 验证 688313 财务数据能获取（Data Gap A）
├── 2. 确认 Qlib 环境正常（Data Gap C）
└── 3. 验证筹码分布数据可用

P1 (本周)
├── 4. 新闻情感打分工具（Data Gap B）
└── 5. 轻量回测工具降级方案（Data Gap C）

P2 (后续)
├── 6. 市场情绪仪表盘（Data Gap B）
└── 7. Tushare 财务数据备源（Data Gap A 增强）
```

---

## 实施结果摘要

### P0（已完成）

| 任务 | 结果 | 证据 |
|-----|------|-----|
| 财务数据 688313 | ✅ 全部可用 | AkShare 返回：摘要 80 行、资产负债 28 行、利润 31 行、现金流 31 行 |
| Qlib 环境 | ✅ 可用（降级机制） | `qlib_bin` 完整（calendars + features + instruments）；`get_qlib_factor_snapshot` 依赖 `qlib_pipeline_service`（优先读 CSV，降级到 AkShare 拉取）；`run_backtest` 自动降级到 pandas 买入持有 |
| 筹码分布 688313 | ✅ 完全可用 | AkShare `stock_cyq_em` 返回 90 行；获利比例 84.99%、平均成本 118.78 |
| 股票管理页面 | ✅ 已修复 | `stock_cache_db.py` 的 `list_stocks_for_admin` / `stock_cache_admin_stats` 从空 stub 实现为真实 DB 查询 |

### P1（已完成）

| 任务 | 结果 | 改动文件 |
|-----|------|---------|
| 新闻情感打分工具 | ✅ 已实现 | `quant_tools.py` 新增 `get_news_sentiment` + `SentimentScoreToolResult`（规则引擎：40 正向 + 40 负向关键词，0-1 分，>0.7 多/<0.3 空） |
| 轻量回测降级 | ✅ 已就位 | `qlib_pipeline_service.py` 的 `run_backtest()` 已有 pyqlib → pandas 降级链；`simple_backtest()` 实现买入持有回测 |

### P2（已完成）

| 任务 | 结果 | 改动文件 |
|-----|------|---------|
| 市场情绪仪表盘 | ✅ 已实现 | `quant_tools.py` 新增 `get_market_mood` + `MarketMoodToolResult`（`stock_market_fund_flow` 涨跌家数 + 快讯情感） |
| Tushare 财务备源 | ✅ 已集成 | `cn_akshare_fundamentals.py` 新增 Tushare 降级逻辑（AkShare 失败时自动尝试 Tushare balance/income/cashflow 接口） |
| TDX gpcw 本地财务数据 | ✅ 已实现 | 新增 `cn_tdx_gpcw.py` Provider + `cn_tdx_gpcw_fields.py` 字段字典 + `get_tdx_financial_data` 工具；识别 `gpsh*.dat`（私有编码）与 `gpcw*.dat`（pytdx 标准格式）的区别；688313 可用 26 期 × 584 字段原始数据，含具名字段映射 |

---

## TDX 本地财务文件 (gpcw*.dat) 分析结论

**文件**: `E:\tdx\通达信金融终端(开心果交易版)V2024.02\vipdoc\cw\gpcw*.dat`
**发现**: `gpsh*.dat` 与 `gpcw*.dat` 是两种完全不同格式的文件

### 两种文件格式对比

| | `gpsh*.dat` (本地预索引) | `gpcw*.dat` (服务器下载) |
|---|---|---|
| 用途 | TDX 本地生成的预索引（私有编码） | 从 `http://down.tdx.com.cn:8001/tdxfin/` 下载 |
| 条目大小 | 26 字节（股票代码无法破��） | 11 字节（标准 pytdx 格式） |
| 股票代码编码 | 6 字节私有编码（无法破��） | 6 字节 UTF-8 可直接解码 |
| pytdx 兼容性 | ❌ 不兼容 | ✅ `HistoryFinancialReader` 可解析 |
| 解析方式 | 无法解析 | `pytdx.reader.HistoryFinancialReader.get_df()` |

### 正确用法（已实现）

1. **数据源**: `vipdoc/cw/gpcw*.dat`（118 个有效文件，从 1988 到 2026）
2. **格式**: pytdx 标准格式 — 20 字节头 + 11 字节/股票索引 + float 数据区
3. **已实现**: `CnTdxGpcwProvider` (`app/infrastructure/providers/cn_tdx_gpcw.py`)
4. **已实现**: `get_tdx_financial_data` 工具 (`quant_tools.py`)
   - 每期 584 个原始浮点字段
   - 688313 从 2017Q4 到 2025Q3 共 26 期
   - 支持 `TDX_ROOT_PATH` 配置

### 字段含义对照表

`stock-analysis/util_docs/专业财务文件字段含义对照表.txt` 包含完整 584 个字段的 1-indexed 对照（1-7 每股指标、8-73 资产负债表、74-105 利润表、98-580 各新增指标）。

已实现: `app/infrastructure/providers/cn_tdx_gpcw_fields.py`（`GPCW_FIELD_NAMES` dict）+ `CnTdxGpcwProvider.get_named_fields()` 方法可将原始值映射为具名 dict。

示例（688313, 20250930）：
- `资产总计: 2548425216.0`
- `营业收入: 1560437376.0`
- `归属于母公司所有者的净利润: 225492.0625`（单位：元）

### 数据对比

| 来源 | 字段数 | 期数 | 备注 |
|------|--------|------|------|
| AkShare 东财 | ~100 具名字段 | 约 8 期 | 有中文名、标准化 |
| **TDX gpcw** | **584 原始字段** | **26 期** | 私有编码、无中文名 |
| Tushare | ~200 具名字段 | 按需 | 需 token |

---

## 关键结论

**报告假设的三类数据缺口已通过本轮实施全部补齐**：

1. **财务数据（Data Gap A）** — AkShare 东财接口已确认 688313 可用；Tushare 降级备源已集成
2. **实时动态（Data Gap B）** — 新增 `get_news_sentiment`（个股舆情量化）+ `get_market_mood`（市场情绪仪表盘）
3. **因子/回测（Data Gap C）** — Qlib 环境可用，轻量 pandas 降级方案已存在于 `qlib_pipeline_service`