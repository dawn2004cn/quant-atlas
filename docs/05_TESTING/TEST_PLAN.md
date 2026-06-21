# 04 测试方案 (Testing & QA)

## 1. 测试策略 (Testing Strategy)
Quant-Atlas 采用四层防御体系：

### 第一层：静态验证 (Static Verification)
*   **py_compile**: 检查所有 `.py` 文件语法，防止运行时崩盘。
*   **Linting**: 修复 F811 (重复导入) 和 E402 (导入顺序)。

### 第二层：功能单元测试 (Unit Testing)
*   **Service Isolation**: 对独立 Service 进行 Mock 测试。
*   **Registry Validation**: 验证 `REQUIRED_SERVICE_ATTRS` 启动时能正确解析。

### 第三层：量化验证 (Quantitative Validation)
*   **Backtest Consistency**: 确保不同版本回测引擎 PnL 一致。
*   **Slippage Simulation**: 验证在 0.1%-0.5% 滑点下的稳健性。

### 第四层：端到端实盘模拟 (Paper Trading)
*   **Mirror Mode**: 实时运行但不下单，对比模拟价与实际价。
*   **Latency Profiling**: 测量从信号产生到 API 发出的端到端延迟。

## 2. 验收标准 (Acceptance Criteria)
*   **Boot-up Zero Warning**: 启动过程无路由跳过或服务缺失警告。
*   **Route Integrity**: 注册路由数匹配预期 (~596+)。
*   **P95 Latency**: 数据湖查询 P95 延迟 $\le 200\text{ms}$。
