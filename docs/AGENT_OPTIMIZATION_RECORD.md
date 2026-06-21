# Agent 系统优化记录

> 本文档记录从 midify_plan10 到 midify_plan13 以及后续优化的完整历程

## 目录

1. [midify_plan10: 基础架构优化](#midify_plan10)
2. [midify_plan11: 架构升维](#midify_plan11)
3. [midify_plan12: 量化巅峰优化](#midify_plan12)
4. [midify_plan13: 集成与组装](#midify_plan13)
5. [后续优化项](#后续优化项)

---

## midify_plan10: 基础架构优化

**目标**: 证据驱动路由、知识中介、自动胜率回溯、LangGraph DTO 集成、动态 Prompt 调优

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 证据驱动智能路由 | `evidence_router.py` | 基于黑板证据的条件跳转，风险信号触发跳过 |
| 知识中介 | `knowledge_intermediary.py` | 证据感知缓存，避免重复工具调用 |
| 自动胜率回溯 | `auto_validator.py` | 后台任务自动计算准确率 |
| 类型化状态 | `typed_state.py` | Pydantic 模型替换 TypedDict |
| 动态 Prompt | `dynamic_prompt.py` | 基于历史错误自适应提示 |

### 核心改进

- 风险信号(delisting_risk, fraud_suspicion)自动跳过 backtest/sentiment 部门
- LRU 缓存 + TTL 过期机制
- 实时胜率排名系统 `get_real_time_rankings()`

---

## midify_plan11: 架构升维

**目标**: 胜率加权投票、魔鬼代言人、冷热分离、动态人格、流式决策、元学习

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 加权共识 | `weighted_consensus.py` | 历史准确率加权投票 + 魔鬼代言人 |
| 分层知识 | `tiered_knowledge.py` | Redis 分布式黑板 + 语义去重 |
| 动态人格 | `dynamic_personality.py` | 市场环境感知人格切换 |
| 响应式管道 | `reactive_pipeline.py` | 流式决策 + 响应式黑板 Observer |
| 元学习 | `meta_learning.py` | Prompt 自动演化 |
| 工具 DTO | `tool_dto.py` | AgentToolResult 结构化输出 |

### 核心改进

- `Final_Score = Σ (Conclusion × Confidence × Historical_Accuracy) / Σ (Confidence × Accuracy)`
- 熊市自动注入"极度恐慌，对利好保持 50% 怀疑"
- High-risk 信号立即 EarlyTermination

---

## midify_plan12: 量化巅峰优化

**目标**: 动态共识权重、反应式黑板、分布式持久化、LLM 分级、决策溯源、环境感知 Prompt

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 动态权重 | `dynamic_weighting.py` | 历史准确率加权聚合 |
| 反应式证据 | `reactive_evidence.py` | EvidenceListener 中断机制 |
| 分布式黑板 | `distributed_blackboard.py` | RedisEvidenceBlackboard |
| 分级 LLM | `tiered_llm.py` | L1/L2 任务分级调度 |
| 决策溯源 | `decision_traceability.py` | AttributionAnalyzer + DecisionHeatMap |
| 环境感知 Prompt | `regime_prompt.py` | 市场情绪锚定 |

### 核心改进

- L1 (GPT-4o-mini) 用于 sentiment/macro，预计节省 40-60% 成本
- 关键证据(盈利下降 50%)触发回测 Agent 重新计算
- DecisionHeatMap 生成 Markdown 热力图报告

---

## midify_plan13: 集成与组装

**目标**: 将所有优化模块真正集成到主流水线

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 统一常量 | `constants.py` | AgentName/BlackboardKey/NodeName 枚举 |
| 集成图谱 | `integrated_graph.py` | 并行部门 + 证据路由 + 权重聚合 |
| 全局工具包装 | `global_tool_wrapper.py` | 证据感知缓存全局拦截 |

### 核心改进

- `DepartmentExecutionNode` 并行执行所有部门
- `evidence_routing_node` 跳过后续部门
- `SynthesisService` 调用 WeightedAggregator + DecisionHeatMap

---

## 后续优化项

### 1. 状态持久化增强 ✅

**文件**: `persistent_memory.py`

- SQLite/PostgreSQL 持久化
- 跨会话胜率追踪
- 自动周期性持久化

### 2. 流式响应支持 ✅

**文件**: `streaming_react.py`

- Token 级流式输出
- `StreamingReactNode` LangGraph 节点
- 支持 tool_calls 间流式输出

### 3. 错误边界与重试 ✅

**文件**: `circuit_breaker.py`

- `CircuitBreaker`: 熔断机制
- `AgentRetry`: 指数退避重试
- `AgentErrorBoundary`: 异常捕获与降级

### 4. 监控与可观测性 ✅

**文件**: `monitoring.py`

- `AgentTelemetry`: OpenTelemetry 风格追踪
- 调用延迟、Token 消耗、成功率统计
- Dashboard 数据聚合

### 5. Redis 会话状态共享 ✅

**文件**: `session_cache.py`

- 多 Worker 状态共享
- Session 恢复与 TTL
- `SessionManager` 生命周期管理

### 6. 配置中心化 ✅

**文件**: `config/agent_config.yaml` + `agents/config.py`

- YAML 配置集中管理
- LLM/Timeout/Retry/CircuitBreaker 配置
- 运行时覆盖支持

---

## 文件清单 (共 30+ 模块)

```
app/agents/
├── constants.py                    # 统一常量管理
├── evidence_blackboard.py         # 证据黑板 (plan10)
├── evidence_router.py             # 证据驱动路由 (plan10)
├── knowledge_intermediary.py       # 知识中介 (plan10)
├── auto_validator.py               # 自动胜率回溯 (plan10)
├── typed_state.py                 # 类型化状态 (plan10)
├── dynamic_prompt.py               # 动态 Prompt (plan10)
├── weighted_consensus.py           # 加权共识 (plan11)
├── tiered_knowledge.py             # 分层知识 (plan11)
├── dynamic_personality.py          # 动态人格 (plan11)
├── reactive_pipeline.py            # 响应式管道 (plan11)
├── meta_learning.py                # 元学习 (plan11)
├── tool_dto.py                     # 工具 DTO (plan11)
├── dynamic_weighting.py            # 动态权重 (plan12)
├── reactive_evidence.py            # 反应式证据 (plan12)
├── distributed_blackboard.py       # 分布式黑板 (plan12)
├── tiered_llm.py                   # 分级 LLM (plan12)
├── decision_traceability.py       # 决策溯源 (plan12)
├── regime_prompt.py                # 环境感知 Prompt (plan12)
├── integrated_graph.py             # 集成图谱 (plan13)
├── global_tool_wrapper.py          # 全局工具包装 (plan13)
├── persistent_memory.py            # 持久化内存 (后续)
├── streaming_react.py              # 流式响应 (后续)
├── circuit_breaker.py             # 熔断机制 (后续)
├── monitoring.py                  # 监控可观测 (后续)
├── session_cache.py                # 会话缓存 (后续)
└── config.py                       # 配置管理 (后续)

config/
└── agent_config.yaml               # Agent 配置文件
```

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Supervisor Node                           │
│                  (LLM Tier Selection)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              DepartmentParallelNode (并行)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Macro   │ │Fundamen-│ │ Technical│ │ Sentiment│        │
│  │Analyst   │ │  tal     │ │ Analyst  │ │ Analyst  │        │
│  │ (L1)     │ │ (L2)    │ │  (L2)    │ │  (L1)    │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       │            │            │            │               │
│       └────────────┴─────┬──────┴────────────┘               │
│                          │                                    │
│                    EvidenceBlackboard                       │
│            (结构化通信 + 知识中介缓存)                         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              EvidenceRoutingNode (早停)                      │
│         风险信号触发 → 跳过耗时应部门                           │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 RiskManager (L2)                             │
│           WeightedAggregator 加权聚合                        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SynthesisNode (决策溯源)                        │
│     DecisionHeatMap + AttributionAnalyzer                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
      AgentMemory                   SessionCache
      (持久化)                      (Redis)
```

---

## 关键指标

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Token 成本 | 100% | ~40-60% (LLM 分级) |
| 部门执行 | 串行 | 并行 (asyncio.gather) |
| 工具调用 | 重复 | 缓存复用 (Knowledge Intermediary) |
| 决策透明度 | 黑盒 | HeatMap 可视化 |
| 系统韧性 | 无 | CircuitBreaker + Retry |
| 配置管理 | 散落 | YAML 集中管理 |

---

*文档更新时间: 2026-04-27*
*累计优化: 30+ 模块*
*架构成熟度: 工业级 → 量化巅峰级*

目前 quant-atlas 的 Agent
  系统已经进化为一个“工业级、闭环演进的多智能体投研大脑”。它不再是简单的线性对话机器人，而是一个结合了层级协作、结构化证据共享、韧性调度和自我进化的复杂架构。

  以下是目前 Agent 系统的全景架构描述：

  ---

  1. 核心架构层 (Core Architectural Layers)

  A. 协同编排层 (Orchestration & Workflow)
   * 层级化团队 (Hierarchical Teams)：通过 TeamSupervisor 管理四个专业部门：基本面部、量化部、风险合规部、情绪部。各部门内部 Agent 并行执行，大幅提升吞吐量。
   * 反应式工作流 (Reactive Pipeline)：利用 LangGraph 实现。不仅支持 Supervisor → Analyst 的分发，还支持基于证据的智能跳转与早停 (Early Exit)。
   * 并行韧性执行 (Parallel Executor)：利用 asyncio 并发驱动 Agent，并结合 CircuitBreaker（熔断器）隔离故障标的或超时的 API。

  B. 共享认知层 (Shared Cognition & Context)
   * 证据黑板 (Evidence Blackboard)：核心通信机制。Agent 不再传递模糊的 Markdown，而是写入强类型的 EvidencePoint（包含键值、置信度、证据强度）。
   * 分布式黑板 (Distributed Blackboard)：支持 Redis 持久化，确保在分布式 Celery Worker 环境下，不同节点上的 Agent 能共享同一研究任务的认知状态。
   * 知识中介 (Knowledge Intermediary)：工具调用的智能拦截层。如果黑板中已有相关数据证据，直接返回缓存，消除重复的行情/财报请求开销。

  C. 认知演进层 (Intelligence & Feedback Loop)
   * 长期记忆与自省 (Agent Memory & Self-Correction)：记录每个 Agent 的决策历史。AgentMemoryInjector 会将该 Agent 过去的“错题”动态注入当前 Prompt。
   * 自动回溯器 (Auto-Validator)：闭环的核心。定时任务自动获取股价走势，比对 Agent 的结论，计算实时胜率（Accuracy Score）。
   * 动态权重聚合 (Dynamic Weighting)：在最终决策时，系统自动调高高胜率分析师的权重，实现元学习 (Meta-Learning)。

  ---

  2. 决策质量与成本优化 (Optimization & Quality)

   * 分级模型调度 (Tiered LLM Orchestration)：
       * L1 (Fast/Cheap)：GPT-4o-mini 处理摘要、过滤等简单任务。
       * L2 (Reasoning)：GPT-4o/Claude 处理深度逻辑推演和风控终审。
   * 环境感知提示词 (Regime-Aware Prompting)：根据 MarketRegimeManager 识别的牛/熊/震荡状态，动态调整 Agent 的“防御性”或“进攻性”人格。
   * 决策可追溯性 (Decision Traceability)：生成决策影响路径图，清晰展示哪些关键证据（如“PE 历史分位低”或“MACD 背离”）对最终 Verdict 产生了决定性影响。

  ---

  3. 数据流转示意 (Data Flow)

   1. 输入：用户 Query + 标的代码。
   2. 规划：Supervisor 读取 Regime 信息，构建初始研究计划。
   3. 并发执行：
       * FundamentalDept 抓取财报 DTO，写入“估值过低”证据。
       * TechnicalDept 拦截 IO，复用黑板数据，写入“趋势突破”证据。
       * EvidenceRouter 检测到核心风险，触发早停或引导至辩论环节。
   4. 博弈辩论：Bull 与 Bear 角色基于黑板证据点进行结构化辩论。
   5. 加权汇总：WeightedAggregator 根据各角色历史胜率，对辩论结果进行加权。
   6. 输出：结构化 DTO 报告 + 可追溯的决策仪表盘。
   7. 异步审计：N 天后，AutoValidator 激活，更新该 Agent 的战绩库。

  ---

  4. 架构设计原则 (SOLID Compliance)
   * 单一职责 (SRP)：每个分析师只处理特定领域的工具与证据，AutoValidator 只负责回溯，互不干涉。
   * 开闭原则 (OCP)：新增 Agent 只需要实现 BaseAgent 接口并在 Department 中注册，无需修改主图逻辑。
   * 依赖倒置 (DIP)：Agent 依赖于 Blackboard 抽象和 AgentPort 接口，而非具体的数据库或 LLM 实现。
   * 接口隔离 (ISP)：通过 EvidenceRouter 实现了不同任务阶段对证据子集的按需访问。

  总结
  该 Agent 系统目前的架构已具备极强的工程健壮性和商业级量化研究能力。它通过“结构化通信”解决了长 Context
  幻觉问题，通过“历史胜率回溯”解决了决策盲目性问题，是一个能够随着交易数据积累而自动进化的“量化数字团队”。