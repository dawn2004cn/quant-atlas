# 02 架构设计与重构文档 (Architecture & Refactoring)

## 1. 系统全景设计 (System Overview)
Quant-Atlas 采用**模块化上下文架构 (Modular Context Architecture)**。系统被划分为多个 `ContextModule`，每个模块拥有自己的服务集、领域对象和配置。

### 核心分层：
*   **Presentation Layer**: Flask API $\rightarrow$ 路由注册 $\rightarrow$ 业务逻辑。
*   **Application Layer**: 协调不同服务完成具体业务流程 (Workflows)。
*   **Domain Layer**: 纯粹的业务逻辑、值对象 (Value Objects) 和实体。
*   **Infrastructure Layer**: 数据库、外部 API 适配器、数据湖存储。

## 2. 核心设计模式 (Design Patterns)
### 2.1 注册中心与接线机制 (Registry & Wiring)
为了避免循环依赖并实现极高的灵活性，系统采用了 `ServiceRegistry` 模式：
*   **Registry**: 全局服务注册表，负责维护所有可用服务的实例。
*   **Wiring**: 通过 `wiring_*.py` 文件定义服务的实例化工厂。服务不再直接 `import` 依赖，而是在 `wire()` 阶段从 Registry 中获取。
*   **Lazy Init**: 很多服务在首次被访问时才进行初始化，减少启动时间。

### 2.2 认知内存织网 (Cognitive Memory Mesh)
实现一种“有记忆”的 AI 架构：
*   **Global Fabric**: 全局向量存储，用于索引决策结论。
*   **Local Memory**: 每个模块拥有独立的 JSONL 存储，记录该领域的特定经验（Lesson）。

## 3. 重构历史 (Refactoring Log)
### 3.1 物理清理 (Physical Cleanup Phase)
**目标**：消除 `app/application/services` 与 `app/modules/*/services` 的双路径混乱。
*   **操作**：将所有服务物理迁移至 `app/modules/` 下，旧路径全部转化为单行 `from ... import *` 的 Shim（垫片）。
*   **结果**：实现了代码结构的单一事实来源 (Single Source of Truth)。

### 3.2 服务去中心化 (Service Decentralization)
**目标**：减轻 `services.py` 的臃肿。
*   **操作**：将服务初始化从集中式的 `create_services()` 迁移到各模块的 `wire()` 方法中。
*   **结果**：`services.py` 行数大幅下降，模块自包含能力增强。

## 4. 计划中的重构：快慢路径分离 (Dual-Path)
为了解决实盘延迟，计划将系统分为：
1.  **Fast Path**: 极简、高性能的 C++/Rust 或纯 Python 路径，负责风控 $\rightarrow$ 下单 $\rightarrow$ 止损。
2.  **Slow Path**: 复杂的 AI 推理、认知分析、策略演化 $\rightarrow$ 异步更新 Fast Path 的参数。
