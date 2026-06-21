# 优化记录

> 来源：AGENT_OPTIMIZATION_RECORD.md, STRATEGY_OPTIMIZATION_RECORD.md, midify_plan[0-13].md, strategy_plan[0-4].md, 及相关优化文件

## Agent 系统优化记录

### midify_plan10: 基础架构优化
**目标**: 证据驱动路由、知识中介、自动胜率回溯、LangGraph DTO 集成、动态 Prompt 调优

| 模块 | 文件 | 功能 |
|------|------|------|
| 证据驱动智能路由 | `evidence_router.py` | 基于黑板证据的条件跳转 |
| 知识中介 | `knowledge_intermediary.py` | 证据感知缓存 |
| 自动胜率回溯 | `auto_validator.py` | 后台自动计算准确率 |
| 类型化状态 | `typed_state.py` | Pydantic 替换 TypedDict |
| 动态 Prompt | `dynamic_prompt.py` | 基于历史错误自适应提示 |

### midify_plan11: 架构升维
**目标**: 胜率加权投票、魔鬼代言人、冷热分离、动态人格、流式决策、元学习

| 模块 | 文件 | 功能 |
|------|------|------|
| 加权共识 | `weighted_consensus.py` | 历史准确率加权投票 |
| 分层知识 | `tiered_knowledge.py` | Redis 黑板 + 语义去重 |
| 动态人格 | `dynamic_personality.py` | 市场环境感知人格切换 |
| 响应式管道 | `reactive_pipeline.py` | 流式决策 + Observer |
| 元学习 | `meta_learning.py` | Prompt 自动演化 |

### midify_plan12: 量化巅峰优化
**目标**: 动态共识权重、反应式黑板、分布式持久化、LLM 分级、决策溯源、环境感知 Prompt

| 模块 | 文件 | 功能 |
|------|------|------|
| 动态权重 | `dynamic_weighting.py` | 历史准确率加权聚合 |
| 反应式证据 | `reactive_evidence.py` | EvidenceListener 中断机制 |
| 分布式黑板 | `distributed_blackboard.py` | RedisEvidenceBlackboard |
| 分级 LLM | `tiered_llm.py` | L1/L2 任务分级调度 |
| 决策溯源 | `decision_traceability.py` | AttributionAnalyzer + DecisionHeatMap |

### midify_plan13: 集成与组装
| 模块 | 文件 | 功能 |
|------|------|------|
| 统一常量 | `constants.py` | AgentName/BlackboardKey 枚举 |
| 集成图谱 | `integrated_graph.py` | 并行部门 + 证据路由 |
| 全局工具包装 | `global_tool_wrapper.py` | 证据感知缓存全局拦截 |

### 后续优化项
| 模块 | 文件 | 功能 |
|------|------|------|
| 持久化内存 | `persistent_memory.py` | SQLite/PostgreSQL 持久化 |
| 流式响应 | `streaming_react.py` | Token 级流式输出 |
| 熔断机制 | `circuit_breaker.py` | CircuitBreaker + 指数退避重试 |
| 监控可观测 | `monitoring.py` | OpenTelemetry 风格追踪 |
| 会话缓存 | `session_cache.py` | 多 Worker 状态共享 |
| 配置管理 | `config/agent_config.yaml` | YAML 集中管理 LLM/Timeout/Retry |

### 关键指标

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Token 成本 | 100% | ~40-60% (LLM 分级) |
| 部门执行 | 串行 | 并行 (asyncio.gather) |
| 工具调用 | 重复 | 缓存复用 |
| 决策透明度 | 黑盒 | HeatMap 可视化 |
| 系统韧性 | 无 | CircuitBreaker + Retry |

---

## 策略系统优化记录

### 1. 因子全生命周期管理
**目标**: 因子 IC/IR 追踪、自动淘汰、正交化

| 模块 | 文件 | 功能 |
|------|------|------|
| 因子看板 | `domain/alpha/factor_manager.py` | `FactorDashboard` 实时追踪 IC/IR |
| 衰减检测 | `domain/alpha/factor_manager.py` | `FactorDecayDetector` IR 低于阈值触发告警 |
| 因子中性化 | `domain/alpha/factor_manager.py` | `FactorNeutralizer` 行业/风格中性化 |

### 2. 动态多策略组合
**目标**: Contextual Multi-Armed Bandit + Meta Strategy
- 策略胜率加权动态调整
- 逻辑：表现差的策略自动调低资金分配

### 3. 环境感知型策略开关
**目标**: 策略在不同市场环境下（牛、熊、震、崩）自动调整参数
- BEAR 时自动收紧止损阈值（从 5% 降至 2%）
- 压力测试自动化

### 4. 高仿真执行引擎
**目标**: 滑点与冲击模型、逐笔撮合模拟
- 基于成交量的冲击成本模型
- Tick-level 模拟处理高频因子

### 5. 策略自愈与自动调优
**目标**: 策略漂移检测与自动修复
- Autopilot 5 步流程：Drift 检测 → 根因分析 → RD-Agent 修复 → 影子测试 → 热切换

---

## RD-Agent + Qlib 三位一体闭环

### 架构升级：Alpha 工厂
- **感知层**: FactorLifecycleManager 实时反馈因子失效
- **决策层**: RD-Agent 根据失效原因动态调整搜索策略
- **流水线**: Qlib Pipeline 自动完成因子生成 → 向量化回测 → 模型蒸馏 → 部署

### 核心突破点
- **演进式因子搜索**: LLM-Aided Heuristics + 多目标优化（与现有组合低相关）
- **无缝数据桥**: Arrow-in-Memory 跳过磁盘转换
- **自动增强**: Multi-Model Ensemble（LightGBM + XGBoost + MLP）

---

## Qlib 部署

- 推荐 Linux/WSL2/Docker；纯 Windows 上 pyqlib 安装易踩坑
- 安装：`pip install -r requirements-qlib.txt`
- ingest 写 `instance/qlib_export/*.csv`；dump 到 `qlib_bin` 需 pyqlib
- 与 Web/Worker/Beat 一起运行，优先阅读 `DEPLOYMENT.md`

---

## TradingAgents 集成

- `TradingAgents-CN` 为可选子项目/参考工程
- 有独立 Docker 说明，主站部署时可按需忽略
- 主应用通过 `app/agents/` 下的 LangGraph 研究图调用

---

*文档更新时间: 2026-04-27*
*累计优化: 30+ 模块*
