通过对 app/agents 模块的二次审计，我发现你已经构建了一个极其庞大且组件化程度极高的 Agent 生态系统（包含 25+
  个独立优化模块）。你已经实现了黑板模式、层级团队、自省记忆、韧性执行、自动回溯、动态提示词、知识中介以及智能路由。

  目前的架构已经具备了成为“行业基准”的潜力，但通过代码阅读，我发现了一个核心瓶颈：

  核心观察：基础架构已达“满级”，但“实战组装”尚未完全对齐
  虽然你在 app/agents/ 目录下实现了大量先进的 .py 模块（如 reactive_evidence.py, dynamic_weighting.py, tiered_llm.py），但目前最主要的入口 app/agents/research/graph.py
  仍然在运行旧的、线性的、基于字符串截断传递信息的逻辑。

  为了更好地发挥这些新增 Agent 的效用，我提出以下“组装与集成”维度的优化建议：

  ---

  1. 将线性 LangGraph 升级为“反应式层级部门”
  现状：graph.py 中的 Node 仍然是 macro -> fundamental -> technical 这种串行结构，且靠 [:4000] 这种字符串截断来传递上下文。
   * 优化建议：
       * 启用 HierarchicalTeams：在 graph.py 中，将六个 Analyst 节点合并为一个 DepartmentExecutionNode。该节点内部调用 TeamSupervisor 并利用 asyncio.gather 并行运行所有部门。
       * 状态结构化：将 ResearchState 彻底重构。不再存储 macro_report: str，而是存储 evidence_keys: list[str]，强制所有节点通过 EvidenceBlackboard 存取结构化证据。

  2. 落地“证据驱动”的熔断与早停 (Early Exit)
  现状：EvidenceRouter 已经实现，但尚未在 graph.py 的 conditional_edges 中应用。
   * 优化建议：
       * 插入早停逻辑：在 fundamental_analyst 之后插入一个 evidence_routing_node。如果黑板中已存在“critical_risk”证据（如退市风险），路由直接跳转至 `risk_manager
         节点，**跳过耗时的 backtest_optimizer`（回测非常昂贵且耗时）**。
       * 效用：极大降低无效的 Token 消耗和等待时间。

  3. 实现 LLM 分级调度 (Tiered Cost Control)
  现状：所有的 react_with_tools 调用通常都使用同一个全局配置的 LLM。
   * 优化建议：
       * 集成 TieredLLMOrchestrator：在 base.py 或 react_loop.py 中引入分级调度。
       * 策略：对于 SentimentAgent（处理大量非结构化新闻）使用 L1 (GPT-4o-mini)；对于 RiskManager（需要深度权衡）使用 L2 (GPT-4o/Claude 3.5)。
       * 效用：在不损失决策质量的前提下，降低 50% 以上的 API 成本。

  4. 自动化胜率回溯的“元学习”闭环
  现状：AutoValidator 已经可以计算胜率，但这些胜率数据（Accuracy Score）目前只停留在日志或数据库中。
   * 优化建议：
       * 动态权重集成：修改 SynthesisService（或决策仪表盘节点），使其在生成最终 final_verdict 时，调用 WeightedAggregator 根据各 Agent 的实时胜率进行加权打分。
       * 胜率反哺提示词：利用 DynamicPromptBuilder 自动将胜率最低的 Agent 的“失败案例”注入到它下一次执行的 sys_prompt 中，强制其进行“错题本”复习。

  5. 解决知识中介的“IO 冗余”
  现状：多个 Agent 可能会重复调用 get_market_data 等工具。
   * 优化建议：
       * 全局拦截工具调用：在 configure_quant_tools 阶段，使用 EvidenceAwareToolWrapper 包装所有工具。
       * 逻辑：如果黑板中已有当日标的 OHLCV 证据，工具直接从黑板读取，不再发起真实 API 请求。

  6. 代码整洁度微调：消除“魔术字符串”
   * 优化建议：目前 Agent 节点名、黑板 Key、部门名散落在各个文件中。建议统一收纳至 app/domain/constants/agent_const.py 中，通过 Enum 管理，防止重构时遗漏。

  总结
  你现在的系统是“满仓的精密零件，但缺少一条自动化的组装线”。

  下一步行动建议：
  修改 app/agents/research/graph.py，将 TeamSupervisor（层级并行）、EvidenceBlackboard（结构化通信）和 EvidenceRouter（智能早停）这三大“杀手锏”真正集成到主流水线中。这将使你的
  Agent 系统从“顺序复读机”进化为“高效并行的投研大脑”。