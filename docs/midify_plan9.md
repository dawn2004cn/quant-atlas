2026-04-27 gemini agent
 1. Agent 现状分析
  系统目前的 Agent 角色分布如下：
   * LangGraph 研究流 (13 个角色)：Supervisor、六大分析师（宏观、基本面、技术、情绪、回测、FinGPT）、四大辩论方（多、空、进取风险、保守风险）、Risk Manager、决策仪表盘。
   * 独立服务 Agent (10+ 个角色)：Kronos（时间序列预测）、QuantML（因子挖掘）、AgenticAnalysis（市场洞察）、FinGPTForecaster（金融专用 LLM）以及各类 Trading Bots。

  核心问题点：
   * 执行链路过长：目前的 graph.py 采用准线性拓扑（Macro -> Fundamental -> Technical -> ...），Agent 越多，端到端延迟越高。
   * 信息密度稀释：Agent 之间主要通过大段文本（Report）传递信息，Supervisor 难以在庞大的 Context 中精准提取关键证据。
   * 工具调用碎片化：20 多个 Agent 都在独立调用 quant_tools，产生了大量重复的行情/财报请求。

  2. 深度整合与效用提升方案

  为了让 20+ Agent 发挥 1+1>2 的效用，我建议实施以下优化架构：

  A. 引入“共享证据黑板” (Shared Evidence Blackboard)
  方案：在 ResearchState 中引入结构化的 Blackboard 对象。
   * 改进：Agent 不再只是产出 Markdown 报告，而是向黑板写入强类型的“证据点（Evidence Points）”。
   * 效用：BullResearcher 在辩论时可以直接引用 TechnicalAnalyst 写入的 support_level 数值，而无需通过 LLM 从长文中二次解析。

  B. 架构升维：从“扁平图”转向“层级化集群” (Hierarchical Teams)
  方案：采用 Supervisor-sub-supervisor 模式。
   * 组织方式：
       * 投研总部 (HQ)：Supervisor 负责分发任务给“部门”。
       * 专业部门 (Department Graphs)：
           * 基本面部：管理估值、财报、行业分析子 Agent。
           * 量化回测部：管理因子、回测、参数优化子 Agent。
           * 风险合规部：管理风险辩论与终审。
   * 效用：缩短主图长度，提升并行度。各部门内部可以实现高度专业化的闭环。

  C. 知识中介化 (RAG-Driven Long-term Memory)
  方案：将 ResearchReportRAGService 深度嵌入 Agent 循环。
   * 改进：Agent 在“思考”前，先检索 LongTermMemory。
   * 效用：如果一个 Agent 在三个月前对该标的有过错误的预判，CriticAgent 能在本次分析中自动引用该历史失败案例进行自省（Self-Correction）。

  D. 统一 Agent 契约与 DTO 化
  方案：定义 BaseAgent 基类和统一的 AgentResponseDTO。
   * 改进：

   1     class AgentResponseDTO(BaseModel):
   2         conclusion: Literal["BULLISH", "BEARISH", "NEUTRAL"]
   3         confidence: float
   4         evidence_keys: list[str]  # 指向黑板中的键
   5         narrative: str            # 供人类阅读的文本
   * 效用：消除 dict.get() 带来的 AttributeError 风险（如之前修复的案例），提高系统鲁棒性。

  E. 并行感知与韧性 (Parallelism & Resilience)
  方案：
   * 并发执行：在 LangGraph 中利用 asyncio.gather 并行运行所有 Analysts。
   * 熔断隔离：利用已实现的 CircuitBreaker。如果 SentimentAnalyst 调用的新闻接口超时，系统应能自动降级，不阻塞其他 19 个 Agent 的工作。

  3. 审核结论与下一步行动
  目前的系统已具备“智库”雏形。下一步优化的核心是“去中心化执行”与“中心化知识共享”。

  建议优先级：
   1. 第一步：将 ResearchState 中的报告字段从 str 逐步升级为包含 metadata 的 DTO。
   2. 第二步：将 20+ Agent 按职责划分进 3-4 个 Sub-graph，由 Supervisor 调度。
   3. 第三步：建立 CommonEvidencePool，实现“一次获取数据，全员共享证据”。

  这些改进将使你的系统从一个“按顺序说话的分析师队列”进化为一个“具备协同进化能力的投研机构”。