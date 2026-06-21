# 02 架构设计与重构 (Architecture & Refactoring)

## 1. 系统全景设计 (System Overview)
Quant-Atlas 采用**模块化上下文架构 (Modular Context Architecture)**。

### 核心分层：
*   **Presentation Layer**: Flask API $\rightarrow$ 路由注册 $\rightarrow$ 业务逻辑。
*   **Application Layer**: 协调不同服务完成具体业务流程 (Workflows)。
*   **Domain Layer**: 纯粹的业务逻辑、值对象 (Value Objects) 和实体。
*   **Infrastructure Layer**: 数据库、外部 API 适配器、数据湖存储。

## 2. 核心设计模式 (Design Patterns)
### 2.1 注册中心与接线机制 (Registry & Wiring)
为了避免循环依赖，系统采用了 `ServiceRegistry` 模式：
*   **Registry**: 全局服务注册表，负责维护所有可用服务的实例。
*   **Wiring**: 通过 `wiring_*.py` 文件定义服务的实例化工厂。服务在 `wire()` 阶段从 Registry 中获取依赖。

### 2.2 认知内存织网 (Cognitive Memory Mesh)
*   **Global Fabric**: 全局向量存储，用于索引跨模块的决策结论。
*   **Local Memory**: 每个模块拥有独立的 JSONL 存储，记录该领域特有的经验（Lesson）。

## 3. 重构历史 (Refactoring Log)
### 3.1 物理清理 (Physical Cleanup)
将所有服务从 `app/application/services` 物理迁移至 `app/modules/` 下，旧路径转化为单行 Shim 垫片，实现代码结构的单一事实来源 (SSOT)。

### 3.2 服务去中心化 (Service Decentralization)
将服务初始化从集中式的 `create_services()` 迁移到各模块的 `wire()` 方法中，减轻 `services.py` 的负担。

## 4. 未来规划：快慢路径分离 (Dual-Path)
*   **Fast Path**: 极简、高性能链路 $\rightarrow$ 风控 $\rightarrow$ 下单 $\rightarrow$ 止损 ($\text{ms}$ 级)。
*   **Slow Path**: 复杂 AI 推理 $\rightarrow$ 认知分析 $\rightarrow$ 策略演化 $\rightarrow$ 异步更新 Fast Path 参数 ($\text{s}$ 级)。
