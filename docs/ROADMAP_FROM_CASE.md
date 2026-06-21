# 对照 `docs/case.md` 的实施路线图（与本仓库现状）

本文将《量化研究监控平台》规划方案（`docs/case.md`）拆为可验收条目，并标注在本项目（Quant Atlas / `app/`）中的**落地状态**，便于与 `docs/roadmap_qlib_rd_agent.md`（Qlib/RD 专项）交叉阅读。  
**如何同时起 Web、Celery Worker、Beat 以发挥 Qlib/RD**：见 **[RUN_STACK_DEPLOY.md](RUN_STACK_DEPLOY.md)**。

---

## 总览对照

| `case.md` 主题 | 本仓库现状 | 缺口 / 持续项 |
|----------------|------------|----------------|
| 数据层：AKShare + TDX + yfinance | `MultiSourceMarketProvider`、TDX 本地、`cn_akshare_*`、Qlib 导出管线 | 期货/外汇多资产 Qlib Handler 未统一；每日一致性校验可加强 |
| Qlib 存储与表达式 | `instance/qlib_export`、`qlib_bin`、`QlibPipelineService`、`QlibService` | 全量 Alpha158/360 内置库导入、Dask/Ray 并行属后续 |
| RD-Agent 因子循环 | `RDAgentRunService`、`rdagent_tasks`、产物注册表、`/api/v1/rd-agent/*` | 与上游 `rdagent fin_quant` 深度耦合、成本控制需运维策略 |
| 模型层 Zoo / MLflow | `ModelPredictLabService`、`/api/v1/predict/*`、量化实验室 | 完整 Qlib Model Zoo、MLflow/W&B 未接 |
| 回测双轨 | 平台策略回测 + `POST /api/v1/qlib/*`、量化实验室对比 | Qlib 官方组合回测、TWAP/VWAP 仿真为后续 |
| UI：仪表盘 / AI 研究 | Jinja 首页、全景、自选股、回测、**AI 研究**导航、量化实验室、研究闭环、消息中心 | TradingAgents-CN SPA 为可选挂载；Streamlit 未用 |
| 因子监控 IC/IR | `FactorCatalogService`、`/api/factor/monitor`、**Celery `FACTOR_IC_CELERY_BEAT` + 消息 `factor_ic_alert`**、**`POST /api/v1/system/factor-ic-check`** | 邮件/企微外链推送仍待接 |
| 用户与角色 | 研究员/交易员/访客；Qlib+RD 写、**基础数据入库**、**全量 AI 研究 / LLM 模型发现** 按角色收敛 | 更细资源配额、GPU 队列监控为后续 |

---

## Phase 1（case：数据 + Qlib 基础）

- [x] 多源行情与缓存（TDX / 网关 / SQLite）
- [x] AKShare → CSV → Qlib bin 管线（`ENABLE_QLIB`、Celery 可选 Beat）
- [x] `GET /api/v1/qlib/health`、`/qlib/status`
- [x] 量化实验室：因子列表、预测占位、回测对比
- [ ] 全市场期货/外汇统一契约（规划中）

## Phase 2（case：RD-Agent + 模型增强）

- [x] RD-Agent 提交与轮询、artifact 注册
- [x] LangGraph 研究内聚于 `app/agents/research`
- [ ] LSTM/Transformer 真训练管线 + ensemble（部分占位）
- [ ] 与 `rdagent` CLI 官方 quant 场景一键对齐（依赖环境与预算）

## Phase 3（case：仪表盘 + 警报 + 权限）

- [x] 任务消息中心（Redis/内存）
- [x] 因子健康摘要 API + 实验室展示（IC 阈值预警）
- [x] 角色：管理员 / 开发者 / **研究员** / **交易员** / 访客；研究型写操作限制
- [x] IC 弱信号：**Beat 定时**（`FACTOR_IC_CELERY_BEAT`）写入消息中心；手动 `factor-ic-check`
- [ ] 外部告警渠道（邮件、企业微信）
- [ ] CSI300 等基准自动化测试套件与文档样例（持续补充）

---

## 相关路径速查

| 能力 | 代码 / 路由 |
|------|-------------|
| Qlib 管线 | `app/application/services/qlib_pipeline_service.py`、`app/presentation/api/routes.py` |
| RD-Agent | `app/application/services/rdagent_run_service.py`、`app/presentation/routes/rdagent_routes.py` |
| 因子目录与监控 | `app/application/services/factor_catalog_service.py`、`/api/factor/list`、`/api/factor/monitor` |
| 研究 UI | `app/presentation/web/templates/quant_lab.html`、`research_pipeline.html` |
| 专项路线图 | `docs/roadmap_qlib_rd_agent.md` |

---

**维护说明**：行为或契约变更时请在根目录 `REFACTORING_LOG.md` 登记；本表侧重「规划 ↔ 实现」追踪，技术细节以 `roadmap_qlib_rd_agent.md` 为准。
