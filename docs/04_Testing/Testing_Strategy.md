# 04 测试文档 (Testing & QA)

## 1. 测试策略 (Testing Strategy)
Quant-Atlas 采用分层测试体系，确保从代码语法到交易逻辑的全面正确性。

### 第一层：静态验证 (Static Verification)
*   **py_compile**: 每次大规模重构后，必须运行 `py_compile` 检查所有 `.py` 文件，防止语法错误。
*   **Linting**: 检查 F811 (重复导入) 和 E402 (导入顺序) 等代码质量问题。

### 第二层：功能单元测试 (Unit Testing)
*   **Service Isolation**: 对独立 Service 进行 Mock 测试，验证核心业务算法。
*   **Registry Validation**: 验证所有 `REQUIRED_SERVICE_ATTRS` 在启动时能正确解析且不为 `None`。

### 第三层：量化验证 (Quantitative Validation)
*   **Backtest Consistency**: 确保同一套参数在不同版本回测引擎中产生的 PnL 一致。
*   **Slippage Simulation**: 验证回测结果在加入 0.1% - 0.5% 滑点后是否依然稳健。

### 第四层：端到端实盘模拟 (Paper Trading)
*   **Mirror Mode**: 策略在实盘环境中运行但不下单，对比模拟成交价与实际成交价。
*   **Latency Profiling**: 测量从信号产生到 API 发出请求的端到端延迟。

## 2. 验收标准 (Acceptance Criteria)
*   **Boot-up Zero Warning**: 启动过程中不得出现 "Route preload skipped" 或 "Service missing" 等警告。
*   **Route Integrity**: 注册路由数必须与预期相符 (当前 ~596+)。
*   **P95 Latency**: 数据湖查询 P95 延迟必须低于 200ms。
