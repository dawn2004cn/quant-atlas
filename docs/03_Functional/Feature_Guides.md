# 03 功能手册 (Functional Guides)

## 1. 认知内存织网 (Cognitive Memory Mesh)
### 核心逻辑
系统不再依赖于巨大的 prompt，而是通过 `MemoryFabric` 动态检索相关经验。
*   **记住 (Remember)**：当一个决策被证明有效/失效时，调用 `remember()` 将结果存入向量库。
*   **回忆 (Recall)**：在生成新决策前，调用 `recall()` 检索类似场景的历史结论，将其作为 Context 注入 LLM。

## 2. 策略向导 (Strategy Wizard)
### 工作流
$\text{模板选择} \rightarrow \text{参数配置} \rightarrow \text{快速预览} \rightarrow \text{部署部署}$
*   **AI 推荐**：系统根据当前的 `MarketRegime` (市场政体) 自动在模板库中高亮最匹配的策略风格。
*   **快速回测**：利用 `FastBacktestEngine` 提供秒级的参数敏感度分析。

## 3. Alpha 市场 (Alpha Marketplace)
### 运行机制
*   **Token 化**：因子被封装为可交易的 Token，包含其历史 IC 值、夏普比率等元数据。
*   **结算流程**：买家支付 $\rightarrow$ 钱包扣款 $\rightarrow$ 解锁信号 API 访问权限 $\rightarrow$ 卖家获得收益。
*   **治理**：引入治理 DAO，通过投票决定哪些高权重因子进入“核心基准库”。
