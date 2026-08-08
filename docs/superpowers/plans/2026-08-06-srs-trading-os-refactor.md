# SRS Trading OS 对齐重构计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。
>
> **规格来源：** `docs/01_Requirements/01_SRS.md`  
> **对照盘点：** 2026-08-06 代码差距矩阵（Research 强；网关/MCP/硬风控/锦标赛硬门槛弱）

**目标：** 在不推倒现有四层架构与研究管线的前提下，把 Quant Atlas 收敛为可验证的「本地优先 Trading OS」——对齐 SRS 的安全底线、统一执行契约、量化 MCP、策略锦标赛硬门槛与前端主轨；对 SRS 中与现实冲突的条目做显式产品决策并回写需求文档。

**架构：** 保留 `presentation → application/modules → domain → infrastructure`；在 Domain 固化统一交易契约与 Risk Guard Port；Infrastructure 挂载 Adapter（QMT/CCXT 先，IBKR/CTP 后）；新增 `scripts/mcp-servers/quant-atlas-mcp` 暴露本地量化工具；Tournament 与 Paper Trading 通过硬门槛服务打通；前端以 React SPA 为主轨（**不**迁 Vue）。

**技术栈：** Python 3.10+、Flask、React+Vite+Tailwind、Celery、Redis、TimescaleDB、qlib CSV/bin、FastMCP、现有 LangGraph research agents

---

## 0. 产品决策（已确认 2026-08-06）

| # | SRS 原文 | 已确认决策 | 理由 |
|---|----------|------------|------|
| D1 | 前端 Vue 3 | **保持 React SPA + 渐进日落 Jinja** | `frontend/` 已是主 SPA；迁 Vue 成本高、无增量价值 |
| D2 | CTP Adapter | **P2；近中期 A 股执行以 QMT 为准** | 仓库已有 `qmt_executor.py`；CTP 仅 vnpy skill 模板 |
| D3 | ClickHouse 与 Timescale 并列 | **权威写入：Timescale + CSV + qlib_bin**；CH/QuestDB 不恢复入库主路径 | 2026-08 入库精简已落地 |
| D4 | FastMCP 暴露交易 API | **新建 quant-atlas-mcp**，与 wind/ifind/akshare 数据 MCP 并存 | 现有 MCP 是外部数据代理，非本地交易面 |
| D5 | IBKR | **P2 独立里程碑** | 当前无实现；不阻塞 P0/P1 |
| D6 | 回测 10 年分钟级 ≤10s | **先建基准测试再优化**，不虚构达标 | 合成 10y 规模（60 万 bar）向量化 **~0.01s**（见 `instance/backtest_minute_10y_vectorized.json`）；**真实行情分钟**仍待独立优化 |

> **状态：用户已确认 D1–D3（及隐含 D4–D6）。**  
> **实施进度（2026-08-08）：** SRS 对齐计划主路径已收束（B–E）。IBKR/CTP 真会话（paper + CONFIRM_LIVE）已接；合成 10y 分钟向量化基准已记录。剩余：真实行情分钟优化、TradeMaster/RL 实盘。

---

## 1. 现状差距摘要（成熟度 0–5）

| SRS 域 | 成熟度 | 关键现状 | 主缺口 |
|--------|--------|----------|--------|
| Research Agent / 辩论 | 4 | `app/agents/research/` | 未与「上线门禁」硬连接 |
| REST API | 4 | `app/presentation/api/` | — |
| Timescale + Redis + qlib | 4 | dayk sync / RedisClientPool / qlib pipeline | 文档与 TRACEABILITY 需更新 |
| CCXT / Paper / QMT | 3 | `ccxt_adapter.py`、`paper_trading.py`、`qmt_executor.py` | 非统一 Gateway 插件模型 |
| 图表 / AI 页 | 3 | Lightweight Charts；`AIChat.tsx` | 非全局侧边栏产品形态 |
| 回测引擎 | 3 | event + vectorized 多引擎 | 阶梯手续费、性能基准缺失 |
| MCP（量化） | 2 | `scripts/mcp-servers/*` 数据代理 | 缺 kline/backtest/portfolio 工具 |
| Tournament（SRS 义） | 1–2 | `evolution_tournament.py` 资源分配 | 无 Sharpe/MDD 硬门槛晋级 |
| Risk Guard | 1–2 | 配置阈值 / 预检 | 无 Flatten All、无连续止损吊销、无 Telegram |
| IBKR / CTP | 0–1 | — / vnpy 模板 | 未实现 |
| LLM 代码 Docker 沙箱 | 2 | builtins / process_runner | 非容器强隔离 |
| API Key 禁提现 | 1 | — | 无策略校验 |

---

## 2. 文件清单（按阶段将创建/修改）

### Phase A — 需求与可追溯（文档）
- 修改：`docs/01_Requirements/01_SRS.md`（写入 D1–D6 决策脚注）
- 修改：`docs/01_Requirements/TRACEABILITY.md`（扩展 REQ 矩阵）
- 修改：`REFACTORING_LOG.md`

### Phase B — P0 安全与执行底线
- 创建：`app/domain/trading/risk_guard.py`（纯领域规则：日回撤 / 连续止损）
- 创建：`app/domain/ports/risk_guard_port.py` 或并入 `app/domain/ports.py`
- 创建：`app/modules/execution/services/risk_guard_service.py`
- 创建：`app/infrastructure/notifications/telegram_alerter.py`（可先 stub + webhook 适配）
- 修改：`app/infrastructure/execution/borderless_router.py`、`qmt_executor.py`、相关 driver（下单前调用 Guard）
- 创建：`app/infrastructure/security/exchange_api_key_policy.py`
- 创建：`app/infrastructure/sandbox/strategy_docker_runner.py`（可选 feature flag）
- 测试：`tests/domain/test_risk_guard.py`、`tests/modules/execution/test_risk_guard_service.py`

### Phase C — P1 统一契约 + MCP + Tournament
- 创建：`app/domain/trading/contracts.py`（`OrderRequest` / `Position` / `Tick` 唯一源）
- 修改：`app/infrastructure/adapters/ccxt_adapter.py`、`app/infrastructure/execution/*` 映射到 contracts
- 创建：`scripts/mcp-servers/quant-atlas-mcp/server.py`
- 创建：`app/modules/strategy/services/tournament/strategy_tournament_service.py`
- 修改：`app/domain/alpha/paper_trading.py`、Celery Beat（非交易时段调度）
- 修改：`app/modules/user/services/nl_strategy_service.py`（codegen 路径对接沙箱回测）
- 测试：`tests/domain/test_trading_contracts.py`、`tests/mcp/test_quant_atlas_mcp_tools.py`、`tests/strategy/test_tournament_gates.py`

### Phase D — P1 前端主轨
- 修改：`frontend/src/`（全局 AI 侧边栏壳、图表指标叠加入口）
- 修改：`app/presentation/web/templates/base.html`（指向 SPA / 日落提示）
- 文档：`docs/DATA_FLOW.md` / `HISTORY_DATA_READ_WRITE_FLOW.md` 保持与入库一致

### Phase E — P2 扩展
- 创建：`app/infrastructure/adapters/ibkr_adapter.py`、`ctp_adapter.py`（或明确「QMT 替代 CTP」后删除本项）
- 修改：回测 engines 阶梯手续费表 + `tests/benchmarks/test_backtest_minute_perf.py`
- 清理：ClickHouse 写入残留任务/文档

---

## 3. 阶段与优先级总览

```text
Phase A  文档决策与 TRACEABILITY     （0.5–1d）
Phase B  P0 Risk Guard + Key 策略 + 下单闸门  （3–5d）
Phase C  P1 契约 + MCP + Tournament 硬门槛   （5–8d）
Phase D  P1 SPA 主轨与 AI 侧边栏             （3–5d）
Phase E  P2 IBKR/CTP/性能/Telegram 完善     （按需）
```

**子系统可拆子计划（建议独立会话执行）：**
1. `…-risk-guard.md` ← Phase B  
2. `…-quant-mcp-and-contracts.md` ← Phase C 前半  
3. `…-strategy-tournament.md` ← Phase C 后半  
4. `…-spa-ai-shell.md` ← Phase D  

本文件是 **主计划**；下面任务可直接开干，也可拆出后引用本文件 §0–§2。

---

## Phase A — 文档与决策落盘

### 任务 A1：回写 SRS 决策脚注

**文件：**
- 修改：`docs/01_Requirements/01_SRS.md`
- 修改：`docs/01_Requirements/TRACEABILITY.md`
- 修改：`REFACTORING_LOG.md`

- [x] **步骤 1：SRS 架构图与 D1–D6 脚注**（已确认后落盘）
- [x] **步骤 2：TRACEABILITY 扩展 REQ-SRS-01…08**
- [x] **步骤 3：REFACTORING_LOG 记录决策确认**
- [ ] **步骤 4：Commit（仅当用户要求提交时）**

```bash
git add docs/01_Requirements/01_SRS.md docs/01_Requirements/TRACEABILITY.md docs/superpowers/plans/2026-08-06-srs-trading-os-refactor.md REFACTORING_LOG.md
git commit -m "docs: confirm SRS product decisions (React/QMT/Timescale)"
```

---

## Phase B — P0 Risk Guard 与执行闸门

### 任务 B1：领域 Risk Guard（纯函数，无 IO）

**文件：**
- 创建：`app/domain/trading/risk_guard.py`
- 测试：`tests/domain/test_risk_guard.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/domain/test_risk_guard.py
from app.domain.trading.risk_guard import RiskGuardDecision, evaluate_account_risk


def test_daily_drawdown_triggers_flatten():
    d = evaluate_account_risk(
        equity=95000.0,
        day_start_equity=100000.0,
        consecutive_stop_outs=0,
        max_daily_drawdown_pct=0.05,
        max_consecutive_stop_outs=3,
    )
    assert d.action == "flatten_all"
    assert d.block_new_orders is True


def test_three_stop_outs_suspend_execution():
    d = evaluate_account_risk(
        equity=99000.0,
        day_start_equity=100000.0,
        consecutive_stop_outs=3,
        max_daily_drawdown_pct=0.05,
        max_consecutive_stop_outs=3,
    )
    assert d.action == "suspend_execution"
    assert d.block_new_orders is True


def test_within_limits_allows_trading():
    d = evaluate_account_risk(
        equity=99000.0,
        day_start_equity=100000.0,
        consecutive_stop_outs=1,
        max_daily_drawdown_pct=0.05,
        max_consecutive_stop_outs=3,
    )
    assert d.action == "allow"
    assert d.block_new_orders is False
```

- [ ] **步骤 2：运行确认失败**

```bash
pytest tests/domain/test_risk_guard.py -v
```

预期：`ModuleNotFoundError` 或 import 失败。

- [ ] **步骤 3：最少实现**

```python
# app/domain/trading/risk_guard.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RiskAction = Literal["allow", "flatten_all", "suspend_execution"]


@dataclass(frozen=True, slots=True)
class RiskGuardDecision:
    action: RiskAction
    block_new_orders: bool
    reason: str


def evaluate_account_risk(
    *,
    equity: float,
    day_start_equity: float,
    consecutive_stop_outs: int,
    max_daily_drawdown_pct: float = 0.05,
    max_consecutive_stop_outs: int = 3,
) -> RiskGuardDecision:
    if day_start_equity <= 0:
        return RiskGuardDecision("suspend_execution", True, "invalid_day_start_equity")
    drawdown = (day_start_equity - equity) / day_start_equity
    if drawdown >= max_daily_drawdown_pct:
        return RiskGuardDecision(
            "flatten_all",
            True,
            f"daily_drawdown={drawdown:.4f}>={max_daily_drawdown_pct}",
        )
    if consecutive_stop_outs >= max_consecutive_stop_outs:
        return RiskGuardDecision(
            "suspend_execution",
            True,
            f"consecutive_stop_outs={consecutive_stop_outs}",
        )
    return RiskGuardDecision("allow", False, "ok")
```

- [ ] **步骤 4：pytest 通过后 Commit（用户要求时）**

---

### 任务 B2：RiskGuardService + 下单闸门

**文件：**
- 创建：`app/modules/execution/services/risk_guard_service.py`
- 修改：`app/infrastructure/execution/borderless_router.py`（或统一下单入口，以实际 `place_order` 路径为准）
- 测试：`tests/modules/execution/test_risk_guard_service.py`

- [ ] **步骤 1：服务职责**

`RiskGuardService.check_before_order(account_id) -> RiskGuardDecision`：读当日权益与连续止损计数（Redis/DB Port），调用 `evaluate_account_risk`。  
`RiskGuardService.on_decision(decision)`：若 `flatten_all` 调用执行 Port 全平；若 `suspend_execution` 写入「执行权限吊销」标志并发告警。

- [ ] **步骤 2：在唯一实盘下单入口最早 return**

伪代码（落到真实函数名时按 Grep `place_order` / `submit_order`）：

```python
decision = risk_guard_service.check_before_order(account_id)
if decision.block_new_orders:
    raise PermissionError(decision.reason)
```

- [ ] **步骤 3：测试用 FakeEquityPort / FakeExecutionPort**，覆盖 flatten 与 suspend 分支。

- [ ] **步骤 4：告警通道** — 优先复用现有 webhook/钉钉；Telegram 实现 `TelegramAlerter`（`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`），未配置则 log + 降级钉钉。

---

### 任务 B3：交易所 API Key 禁提现策略

**文件：**
- 创建：`app/infrastructure/security/exchange_api_key_policy.py`
- 修改：CCXT 初始化路径（`ccxt_adapter.py` 或配置加载处）
- 测试：`tests/infrastructure/test_exchange_api_key_policy.py`

- [ ] **步骤 1：策略对象**

```python
@dataclass(frozen=True)
class ApiKeyPolicy:
    allow_trade: bool = True
    allow_read: bool = True
    allow_withdraw: bool = False  # SRS: 严禁提现
```

启动时若配置声明 `enable_withdraw=True` → **拒绝启动适配器**并 error log。  
无法远程探测权限的交易所：写入审计日志 `assumed_no_withdraw=True`，文档要求运维在交易所后台关闭提现。

---

### 任务 B4：LLM 策略代码沙箱（P0 最小可用）

**文件：**
- 修改：`app/infrastructure/agent/backtest/process_runner.py`（收紧）
- 创建：`app/infrastructure/sandbox/strategy_docker_runner.py`（`STRATEGY_SANDBOX=docker|process`）
- 测试：恶意 `os.system` / 写 `/etc` 必须失败

- [ ] **步骤 1：** 默认 `STRATEGY_SANDBOX=process` 保持现状但禁止网络（若可行）与写仓库外路径。  
- [ ] **步骤 2：** `STRATEGY_SANDBOX=docker` 时用只读挂载 + 无网络 + CPU/内存限制跑回测；无 Docker 则明确 error，禁止静默回退到不安全执行。

---

## Phase C — P1 统一契约、MCP、锦标赛

### 任务 C1：Domain 统一交易契约

**文件：**
- 创建：`app/domain/trading/contracts.py`
- 测试：`tests/domain/test_trading_contracts.py`

```python
# 目标形状（字段可按现有 BorderlessOrderRequest 对齐后冻结）
@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol: str
    market: str  # CN|US|HK|CRYPTO|FUT
    side: Literal["buy", "sell"]
    quantity: float
    order_type: Literal["market", "limit"]
    price: float | None = None
    client_order_id: str | None = None


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    market: str
    quantity: float
    avg_price: float
    unrealized_pnl: float | None = None


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    market: str
    last: float
    bid: float | None
    ask: float | None
    ts: float  # unix seconds
```

- [ ] Adapter（CCXT / QMT / paper）**只**接受/返回上述类型；Go `gateway` 侧后续做 DTO 映射（本阶段可不改 Go，先 Python 统一）。

---

### 任务 C2：quant-atlas-mcp（SRS 三工具）

**文件：**
- 创建：`scripts/mcp-servers/quant-atlas-mcp/server.py`
- 创建：`scripts/mcp-servers/quant-atlas-mcp/README.md`
- 测试：`tests/mcp/test_quant_atlas_mcp_tools.py`（可 mock 应用服务）

- [ ] **工具契约（必须）：**

| Tool | 行为 | 后端 |
|------|------|------|
| `get_historical_kline(symbol, timeframe, limit)` | 返回 OHLCV | 现有 history / Market facade（Timescale 优先） |
| `execute_backtest(strategy_code, params)` | 沙箱回测 | `STRATEGY_SANDBOX` + backtest runner |
| `get_portfolio_status()` | 持仓与 PnL | portfolio / paper / 实盘 Port |

- [ ] 每个 tool 返回结构需含 `evidence` / `confidence`（与项目 Agent 规范一致）或明确 MCP 层包装。  
- [ ] README：如何用 `mcp` CLI / Cursor `mcpServers` 挂载；**默认只读 + 回测**，实盘下单另开 flag。

---

### 任务 C3：策略锦标赛硬门槛 + Paper 池

**文件：**
- 创建：`app/modules/strategy/services/tournament/strategy_tournament_service.py`
- 修改：`app/domain/alpha/evolution_tournament.py`（保留资源分配，或委托给新服务，避免双重语义）
- 修改：Celery Beat（非交易时段任务）
- 测试：`tests/strategy/test_tournament_gates.py`

- [ ] **晋级规则（SRS）：** `Sharpe > 1.8` **且** `MDD < 0.12`（可配置，默认按 SRS）。  
- [ ] 通过者写入 Paper Trading 策略池（`paper_trading.py`）。  
- [ ] 未通过者标记 `rejected` + 原因，不触达实盘权限。  
- [ ] Beat：仅在配置的非交易窗口运行（复用现有交易日历工具）。

```python
def passes_tournament_gates(sharpe: float, max_drawdown: float) -> bool:
    return sharpe > 1.8 and max_drawdown < 0.12
```

---

### 任务 C4：NL → 策略代码闭环（增量）

**文件：**
- 修改：`app/modules/user/services/nl_strategy_service.py`
- 测试：现有 NL 测试 + 新增「生成代码必须走沙箱回测才可标记 ready」

- [ ] 不在本阶段追求任意 Python codegen 完美；最小闭环：生成或选定策略源码 → `execute_backtest`（同 MCP）→ Risk/Bias 检查（复用 `bias_detector.py`）→ 才可进入 Tournament 候选池。

---

## Phase D — P1 前端主轨

### 任务 D1：SPA 为唯一交互主轨声明

**文件：**
- 修改：`frontend/src/` 布局（App shell）
- 修改：导航与 `docs` 中「经典页」说明

- [ ] 全局 **AI Assistant 侧边栏**（可折叠）：复用 `AIChat` 能力，挂到主 layout，而非仅独立路由。  
- [ ] TradingView Lightweight Charts：在股票详情 SPA 路由统一画线/指标入口（已有 vendor 则接线，不新引入 Vue）。  
- [ ] Jinja：新功能禁止新增；旧页加「前往 SPA」横幅（可选）。

---

## Phase E — P2（按需排期）

| 任务 | 验收 |
|------|------|
| E1 IBKRAdapter | 能拉美股仓位/下模拟单；映射 `OrderRequest` |
| E2 CTP 或正式文档「以 QMT 替代」 | SRS 与 TRACEABILITY 一致 |
| E3 阶梯手续费表 | 回测报告含 fee_schedule_id |
| E4 分钟级回测基准 | `tests/benchmarks/` 记录基线；未达标不宣称 SRS 性能 |
| E5 Redis 行情延迟指标 | 暴露 p50/p95；告警阈值可配（目标 50ms 为 SLO 而非门禁） |
| E6 清理 CH 写入文档/任务残留 | 与 2026-08 入库精简一致 |

---

## 4. 验证策略

| 级别 | 命令 / 动作 |
|------|-------------|
| 单测 | `pytest tests/domain/test_risk_guard.py tests/strategy/test_tournament_gates.py -q` |
| 执行闸门 | 集成测试：Guard suspend 后 `place_order` 必失败 |
| MCP | 本地启动 quant-atlas-mcp，用 MCP inspector 调三工具 |
| 回归 | `pytest tests/application/test_scheduled_cn_history_daily.py tests/architecture/test_phase_e_observability.py -q` |
| 文档 | 每阶段更新 `REFACTORING_LOG.md` + TRACEABILITY |

---

## 5. 明确不做（YAGNI）

- 不把 Flask 整体迁 FastAPI / 不迁 Vue。  
- 不恢复 MySQL/QuestDB/CH **历史入库**主路径。  
- 不在 P0 重写 Go `gateway` 或全量删除 Jinja。  
- 不做「神类再拆」大架构运动（见 `2026-06-28-architecture-refactor-plan.md`）——与本 SRS 对齐计划解耦，另排期。  
- 不把 Research LangGraph 换成另一套 Agent 框架。

---

## 6. 建议执行顺序（第一周）

1. ~~用户确认 **§0 D1–D6**~~ ✅ 2026-08-06  
2. ~~任务 A1 文档~~ ✅  
3. ~~任务 B1 → B4（Risk Guard / Key / 沙箱）~~ ✅  
4. ~~任务 C1–C4 + MCP/Paper 深接~~ ✅  
5. ~~Phase D1 全局 AI 侧边栏~~ ✅  
6. ~~锦标赛 Beat + contracts 映射 + MA 叠加~~ ✅  
7. ~~Phase E 首批 + SLO/适配器可见性~~ ✅  
8. **长期可选：** 10 年**真实**分钟数据性能优化（合成 10y 向量化基准已达标）；TradeMaster 全套 / RL 实盘

本 SRS 对齐主计划可视为**可交付收束**；后续按独立里程碑推进。
