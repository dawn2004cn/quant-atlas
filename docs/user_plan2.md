以下是为您提出的 Quant Atlas 3.0: “智能与自主” 重构计划，旨在从“工具集合”转向“全自主研究操作系统”：

  1. 架构重构：从“硬编码组装”转向“自发现微内核”

  目前的 service_wiring.py 已经接近 4 万字节，充斥着大量的 try-except 和手动注入逻辑，这在开发者增加新功能时会产生较高的心智负担。

   * 解耦引导程序 (Decoupled Bootstrapping):
       * 引入 Service Registry: 建立一套服务注册机制。服务不再由 service_wiring.py 显式创建，而是通过类装饰器（如 @register_service(scope="singleton")）声明。
       * 模块化生命周期: 仿照内核模块，让 QLib、TDX、AI Swarm 等大块功能成为独立的 AppModule。每个模块拥有自己的 setup()、teardown() 和 register_routes()。
       * 价值： 极大地精简 bootstrap 逻辑，新功能只需在一个文件夹内添加代码即可自动集成，实现真正的“热插拔”。

   * 建立事件总线内核 (Event-Driven Core):
       * 内部 Pub/Sub: 引入全局事件总线（基于 blinker 或内置信号）。
       * 逻辑： 当 SignalGenerated（信号产生）或 TaskCompleted（任务完成）时，不再由 Service A 手动调用 Service B，而是发出事件。
       * 价值： 彻底解决循环依赖问题，使系统能够轻松支持“当 A 发生时，自动触发 B”的联动逻辑。

  2. 功能重构：从“静态偏好”转向“主动个性化”

  目前的 AgentContext 主要是静态数据结构，缺乏对用户意图的深度理解和持续进化。

   * 用户知识图谱 (User Knowledge Service):
       * 超越 Dataclass: 将 UserPreference 升级为持久化的知识服务。记录用户偏好的指标组合、对特定行业的关注度、以及历史上的成功决策模式。
       * 上下文自动增强: 当用户发起研究时，AgentContext 会自动关联“用户历史最关注的相关证据”，让 AI 的回复更贴合个人风格。
       * 价值： 平台将越用越聪明，成为真正的“私人投研官”。

   * 决策证据可视化 (Evidence Graphing):
       * 功能： 在 DecisionContext 的基础上，提供可视化的证据追踪视图。
       * 逻辑： 点击 AI 推荐的股票，前端展示一个有向图：行情数据 -> 选股能力 -> AI 逻辑推理 -> 最终结论。
       * 价值： 解决 AI “黑盒”问题，让用户敢于信任并执行 AI 建议。

  3. 交互重构：从“仪表盘”转向“响应式工作区”

   * 统一实时流网关 (Unified Realtime Stream):
       * 全栈流式化: 将现有的 Socket.IO 零散实现整合为 RealtimeGateway。
       * 内容： 不仅流式推送行情，还要流式推送 “AI 的思考过程” 和 “系统异常自愈状态”。
       * 价值： 用户在 Web 端能看到后台 Agent 正在扫描哪支票、正在产生什么逻辑，显著降低焦虑感。

   * Jarvis 指令深度集成 (Command-First UI):
       * 功能： 极大地增强现有的 Command Orb。支持复合指令，如：“如果 600519 跌破 20 日线且 RSI 小于 30，请通过邮件提醒我，并生成一份技术面分析报告”。
       * 价值： 减少用户在 50 多个页面间跳转的操作成本。

  4. 实施建议 (Next Steps)

   1. 第一步： 重写 service_wiring.py 中的关键服务为声明式注册。
   2. 第二步： 在 app/core 下建立 events.py，作为全系统的神经中枢。
   3. 第三步： 升级 pages.py 的路由加载模式，支持按模块自动扫描（减少该文件长度）。

  通过此计划，Quant Atlas 将从一个“功能强大的平台”进化为一个“能自动响应用户意图并具有自我演化能力的智能体”。