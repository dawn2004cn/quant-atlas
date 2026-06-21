# Quant Atlas - 架构测试与交付策略

本策略定义了重构后系统的测试标准与自动化交付流程。

## 1. 测试标准 (Testing Strategy)
基于 DI 容器的 Mock 模式，建立三层测试金字塔：

*   **单元测试 (Unit Tests)**：
    *   **职责**：验证业务逻辑（Service/UseCase层）。
    *   **手段**：通过 `Container.override()` 注入 `unittest.mock` 的 Repository 接口实例。
    *   **示例**：参考 `tests/test_user_service_di.py`，确保不接触任何数据库连接。
*   **集成测试 (Integration Tests)**：
    *   **职责**：验证基础设施与适配器逻辑（Repository/Adapter层）。
    *   **手段**：使用独立的测试数据库或容器化 MySQL，通过 DI 容器注入真实的 MySQL Repository。
*   **系统/端到端测试 (E2E Tests)**：
    *   **职责**：验证 API 接口与业务完整链路。
    *   **手段**：使用 `Flask` 的 `test_client`，配合完整的 `Container` 配置。

## 2. CI/CD 自动化集成 (Pipeline Strategy)
为了确保重构后的架构不发生回归，CI 流程应包含以下步骤：

### 阶段定义
1.  **静态分析 (Linting)**：
    *   执行 `ruff` 检查代码规范与类型安全性。
2.  **DI 环境验证**：
    *   执行所有以 `_di.py` 结尾的单元测试，确保服务依赖图在各种配置下均能正确组装。
3.  **单元回归测试**：
    *   运行 `pytest --cov=app tests/`，要求覆盖率不低于重构前水平。

### CI 示例 (GitHub Actions)
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - name: Run DI Unit Tests
        run: pytest tests/ -k "_di.py"
      - name: Run Integration Tests
        run: pytest tests/ -m "integration"
```

## 3. 交付策略
*   **配置管理**：所有 DI 容器的环境依赖（如 `DATABASE_URI`）均通过环境变量注入，确保代码与环境配置解耦。
*   **回滚方案**：由于已剥离 `bootstrap_components`，若新架构出现异常，可快速切换 `Container` 的 Provider 定义进行热修复。
