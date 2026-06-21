以下是从“以用户为中心”出发的架构与功能重构计划：

  1. 核心理念：从“资源中心”转向“任务/工作流中心”
  目前的架构高度模块化，但功能较为分散（例如 routes_v1_*.py 超过 50 个）。用户（开发者或终端交易者）往往需要跨多个模块完成一个目标。

  重构目标：
   * 用户侧： 提供统一的“任务中枢 (Workflow Hub)”，让长耗时任务（如 AI 选股、回测、数据同步）具有一致的进度跟踪、异常恢复和人工介入机制。
   * 架构侧： 引入 Workflows 层，将分散在 application/services 中的业务编排逻辑提取到显式的工作流状态机中。

  ---

  2. 架构重构建议

  A. 引入“工作流脊柱 (Workflow Spine)”
   * 现状： AgentWorkflow 仅在领域层定义，未贯穿全栈。
   * 方案： 建立统一的任务执行框架。
       * 在 app/application/workflows 下创建：ResearchWorkflow（研究流）、TradingWorkflow（交易流）、DataPipelineWorkflow（数据流）。
       * 用户价值： 用户可以在“任务中心”看到所有后台任务的实时进度、证据链（Evidence）和等待人工确认的断点（Human-in-the-loop）。

  B. 插件化能力引擎 (Plugin-based Capability System)
   * 现状： ToolFacadeService 承担了过多的具体工具包装，每增加一个新工具都需要修改该服务。
   * 方案： 将 ToolFacadeService 重构为 Plugin Registry。
       * 定义 BaseCapability 接口，允许 infrastructure 中的适配器（如 Qlib, TDX, LLM）自注册能力。
       * 开发者价值： 增加新策略或数据源只需实现接口并打上装饰器，无需修改核心路由或门面服务。

  C. DTO 驱动的类型安全体系
   * 现状： 虽然有 v2 接口，但 v1 仍大量使用原生字典，导致前后端契约模糊。
   * 方案： 全面铺开 Pydantic DTO。
       * 在 app/domain/dto 定义业务对象，在 presentation/api 强制校验。
       * 开发者价值： 自动生成的 API 文档更准确，前端开发可基于 schema 自动生成 TypeScript 类型。

  ---

  3. 功能增强建议（用户视角）

  A. 可观测性与健康自愈 (Self-Healing Observability)
   * 重构点： 现有的 _ux_env_hints 零散分布在 pages.py。
   * 新功能： 建立 "System Pulse"（系统脉搏） 模块。
       * 实时监控 MySQL、Redis、Celery、TDX、LLM API 的连接状态。
       * 用户价值： 当功能不可用时，UI 不再只是报错，而是提供“一键排查”或“修复建议”按钮。

  B. 数据血缘与决策回溯 (Decision Provenance)
   * 重构点： 用户在看 AI 推荐时，往往不清楚为什么推荐。
   * 新功能： 在 domain/entities.py 中增加 DecisionContext。
       * 记录决策时的输入数据快照、模型版本、推理过程及对应的 EvidenceNote。
       * 用户价值： 点击推荐股票，能瞬间回溯到产生该决策的原始行情和 AI 论据。

  C. 统一交互界面 (Unified Interface Hub)
   * 重构点： Web 路由过于扁平化（/backtest, /ai-analysis, /alpha-factory 等并列）。
   * 新功能： 按照 用户旅程 重新组织页面结构：
       * 发现 (Discovery): 市场全景、龙虎榜、热点板块。
       * 研究 (Research): 研报中枢、AI 诊股、因子工厂。
       * 执行 (Execution): 策略回测、信号监控、模拟账户。

  ---

  4. 实施路线图 (Implementation Roadmap)

   1. 阶段一 (Foundation): 统一 app/application/dto 规范，重写 ToolFacadeService 为自注册模式。
   2. 阶段二 (Process): 将 AgentWorkflow 提升为应用层核心，重构 Celery 任务使其支持状态持久化与 Web 实时同步。
   3. 阶段三 (Experience): 合并重复的 Web 模板，引入组件化前端思维（如基于现有 Jinja2 封装更通用的 UI Components）。
   4. 阶段四 (Refinement): 全面升级 actionable_error_catalog，确保每一个系统异常都有对应的用户引导。

  总结
  重构后的 quant-atlas 将不再是一堆工具的集合，而是一个具有“记忆”和“意识”的 AI 量化助手。架构上从“分层被动调用”转向“工作流主动驱动”，从根本上提升平台作为生产力工具的属性。