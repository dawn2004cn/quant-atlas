# 需求 ↔ 代码可追溯矩阵

| 需求 ID | 说明 | 关联模块 | 关键实现文件 |
|---|---|---|---|
| REQ‑001 | 实时行情查询 | market_service | app/modules/market/services/market_service.py |
| REQ‑005 | AI 交易建议 | ai_analysis_service | app/modules/ai_agent/services/ai_analysis_service.py |
| REQ‑010 | 风险控制（仓位上限） | risk_control_service | app/modules/risk/services/risk_control_service.py |
| REQ-SRS-01 | Risk Guard：日回撤≥5% Flatten；连续止损≥3 暂停执行 | risk_guard_service | `app/domain/trading/risk_guard.py`；`app/modules/execution/services/risk_guard_service.py`；闸门：`borderless_router.submit_order` + `driver_registry` |
| REQ-SRS-02 | 量化 FastMCP：kline / backtest / portfolio | quant-atlas-mcp | `scripts/mcp-servers/quant-atlas-mcp/server.py` |
| REQ-SRS-03 | 统一 OrderRequest / Position / Tick | domain.trading.contracts | `app/domain/trading/contracts.py` |
| REQ-SRS-04 | Tournament 硬门槛 Sharpe>1.8 且 MDD<12% | strategy_tournament_service | `app/modules/strategy/services/tournament/` |
| REQ-SRS-05 | Paper Trading 池随锦标赛晋级更新 | paper_trading + PaperTradingPoolAdapter | `app/domain/alpha/paper_trading.py`；`tournament/paper_pool_adapter.py` |
| REQ-SRS-06 | 前端主轨 React SPA（不迁 Vue） | frontend | frontend/src/ |
| REQ-SRS-07 | 近中期执行 QMT；IBKR/CTP=P2 | qmt_executor / adapters | `qmt_executor.py` + `qmt_order_bridge.py`；`ibkr_adapter.py` / `ctp_adapter.py` + `broker_session.py`（仿真/dry-run/ib_insync；CTP 注入 trader；CONFIRM_LIVE） |
| REQ-SRS-08 | 历史 K 权威写入 Timescale+CSV+qlib | tdx_dayk / qlib pipeline | app/modules/data/services/；Celery scheduled_cn_history_daily |
| REQ-SRS-09 | Bias 硬门禁 → Tournament/Paper | bias_detector + tournament | `app/domain/backtest/bias_detector.py`；`tournament/gates.py` |
| REQ-SRS-10 | Feature Pipeline（FreqAI 形态） | feature_pipeline | `app/domain/alpha/feature_pipeline.py`；`routes_v1_feature_pipeline.py` |
| REQ-SRS-11 | RL 研究旁路，默认不进 live | rl_research | `app/domain/alpha/rl_research.py`；`/strategy/rl-research/*` |
| REQ-SRS-12 | 10 年分钟回测先基准后优化（D6） | minute_engine | `app/domain/backtest/minute_engine.py`；`tests/benchmarks/test_backtest_minute_perf.py`；产物 `instance/backtest_minute_*.json` |

> 产品决策 D1–D6 已确认（2026-08-06）。实施计划：`docs/superpowers/plans/2026-08-06-srs-trading-os-refactor.md`。DIF 续项：`docs/superpowers/plans/2026-08-06-dif-borrow-optimize.md`。
