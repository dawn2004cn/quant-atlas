# 03 功能手册 (Functional Guides)

## 1. 认知内存织网 (Cognitive Memory Mesh)
### 核心逻辑
系统通过 `MemoryFabric` 动态检索相关经验，而非依赖超长 Prompt。
*   **记住 (Remember)**：将证明有效/失效的结论存入向量库。
*   **回忆 (Recall)**：在生成新决策前，检索类似场景的历史结论作为上下文注入 LLM。

## 2. 策略向导 (Strategy Wizard)
### 工作流
$\text{模板选择} \rightarrow \text{参数配置} \rightarrow \text{快速预览} \rightarrow \text{部署}$
*   **AI 推荐**：根据 `MarketRegime` 自动高亮最匹配的策略风格。
*   **快速回测**：利用 `FastBacktestEngine` 提供秒级参数敏感度分析。

## 3. Alpha 市场 (Alpha Marketplace)
### 运行机制
*   **Token 化**：因子封装为包含 IC 值、夏普比率等元数据的 Token。
*   **结算流程**：买家支付 $\rightarrow$ 钱包扣款 $\rightarrow$ 解锁信号 API $\rightarrow$ 卖家得利。
*   **治理**：通过治理 DAO 决定哪些高权重因子进入核心基准库。
