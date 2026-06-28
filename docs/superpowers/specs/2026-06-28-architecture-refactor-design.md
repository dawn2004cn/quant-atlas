# 架构重构设计：消除职责重复、神类与重复层

## 背景
通过深度代码审计，发现以下主要架构问题：
1. 三重 Facade 层（app/facade/, app/application/facade/, app/application/facades/）造成接口混乱
2. Domain 层膨胀至 324 文件、50+ 子包，混入应用服务、基础设施逻辑
3. Modules 与 Infrastructure 子包名重复（execution、market、strategy、portfolio 等），导致职责不明确
4. 存在多个 God Classes（>900 行），如 institution_tier_service.py (964行)、trend_breakout.py (946行)
5. 重复的端口定义：domain/ports.py (薄接口) 与 domain/ports/ (63 文件、239 行)
6. 已废弃的 app/services/ 兼容层未清理
7. 路由分散，缺乏按微服务聚合
8. 测试覆盖率约 20%，大量代码缺乏单元测试

本设计提出一个分阶段的重构计划，旨在恢复清晰的四层架构（Presentation → Application → Domain → Infrastructure），消除职责重复，提高模块独立性和可测试性。

## 目标状态（四层架构）

```
app/
├── presentation/          # HTTP、模板、路由、会话
├── application/           # 用例编排、事务边界、权限校验（仅依赖 domain.ports）
├── domain/                # 仅：实体、值对象、枚举、端口接口、纯分析逻辑（无外部依赖）
├── infrastructure/        # 端口实现：仓储、外部 API、消息、适配器（仅依赖 domain）
└── core/                  # 日志、工厂、配置、工具函数（最小依赖）
```

### 允许依赖（自上而下）
- Presentation → Application、Domain、Config
- Application → Domain（仅通过 ports）
- Domain → 仅标准库 / typing（不依赖 Infrastructure、Presentation）
- Infrastructure → Domain
- Core → 根据需要依赖任意层（但尽量保持独立）

## 重构计划（分阶段）

### 阶段 0：准备工作
- 为每个待修改的文件创建单元测试基线（如无则补测补测）
- 确保所有测试通过（`pytest -q` 无失败）
- 建立分支 `architecture/refactor-v1` 进行开发

### 阶段 1：清理可见的职责重复与死代码（可并行）
| 任务 | 动作 | 文件 |
|------|------|------|
| 1.1 | 删除 `app/services/`（已标记废弃的兼容层）| `app/services/` 全部（若有有用内容先迁移） |
| 1.2 | 删除空的重复目录 `app/application/facades/` | `app/application/facades/` |
| 1.3 | 统一端口定义：保留 `app/domain/ports.py` 作为唯一真实接口；废弃 `app/domain/ports/` 目录（将其中的有用接口搬进 `app/domain/ports.py`，其余删除） | `app/domain/ports/` → 删除，`app/domain/ports.py` 合并 |
| 1.4 | 清理 `app/facade/` 中非 shim 的文件，仅保留必需的 shim（在 shim 替换完成后）| `app/facade/`（除 shim 外）|

### 阶段 2：Domain 净化（核心阶段）
目标：确保 `domain/` 仅包含：实体、值对象、枚举、端口接口、纯分析逻辑（无数据库、无外部 API、无消息队列）。

#### 批次 B1：明显不属于 domain 的搬出
- `app/domain/services/` → `app/application/services/`
- `app/domain/workflow*` → `app/application/services/` 或 `app/application/workflows/`
- `app/domain/*/service.py`（命名暗示应用服务）→ 按职责判断迁移

#### 批次 B2：带有外部依赖的分析模块
- 对每个 `app/domain/analysis/*` 和 `app/domain/*/analysis*`：
  - 若仅使用标准库/typing → 保留在 domain/
  - 若有任何数据库访问、外部 HTTP 调用、消息发送 → 迁移至 `app/application/services/`

#### 批次 B3：大型模型/实体检查
- 对每个大型文件（>400 行）在 domain/ 中：
  - 拆分出纯模型（仅数据结构、验证、纯计算）保留在 domain/
  - 拆分出业务逻辑（包含外部依赖）迁移至 `app/application/services/` 或 `app/infrastructure/`

#### 批次 B4：值对象与枚举
- 保留所有值对象和枚举在 domain/（除非混入了业务逻辑，则拆分）

### 阶段 3：拆分 God Classes（>900 行）
目标：将每个大文件拆分为职责单一的小文件（200-400 行），每个文件有明确的单一职责。

#### 目标列表（根据之前统计）：
1. `app/modules/system/services/institution_tier_service.py` (964行)
   → 拆分为：
   - `institution_tier_query_service.py`（只读查询）
   - `institution_tier_update_service.py`（更新/写入）
   - `institution_tier_validator.py`（业务规则校验）
   - `institution_tier_factory.py`（对象创建，若需要）

2. `app/models/trend_breakout.py` (946行)
   → 拆分为：
   - `trend_breakout_model.py`（纯模型：数据结构、验证、纯计算）
   - `trend_breakout_service.py`（业务逻辑：需要外部依赖的操作）

3. `app/infrastructure/repositories/mysql/mysql_tdx_dayk_repository.py` (901行)
   → 拆分为：
   - `mysql_tdx_dayk_read_repository.py`（只读操作）
   - `mysql_tdx_dayk_write_repository.py`（写入操作）
   - `mysql_tdx_dayk_migration_repository.py`（Schema 迁移/初始化）

> 每个拆分后的文件应有明确的单一职责，便于单元测试。

### 阶段 4：分层依赖验证
完成上述搬迁和拆分后，运行依赖检查脚本确保无逆向依赖：
- 使用自定义脚本或 `pyreverse` 检查：
  - `domain/` 不得导入 `infrastructure/`、`application/`、`presentation/`
  - `application/` 不得导入 `infrastructure/`（除通过 ports 注入的实例外）
  - `infrastructure/` 可依赖 `domain/` 与 `core/`
- 修复任何违规。

### 阶段 5：测试与质量提升
- 对每个新建或搬迁的文件，编写单元测试覆盖主要业务路径（目标：新增代码测试覆盖率 ≥ 80%）
- 修复在重构过程中发现的遗漏测试
- 运行全套测试确保无回归（`pytest -q`）

### 阶段 6：文档与交付
- 更新 `docs/architecture/` 相关文档反映新结构
- 在 `REFACTORING_LOG.md` 记录本次重构
- 若需要，编写迁移指南给其他开发者

## 预期影响

| 指标 | 重构前 | 重构后（目标） |
|------|--------|----------------|
| Domain 文件数 | 324+ | ≈180-200（仅实体/值对象/枚举/接口/纯分析） |
| 应用服务文件数 | 分散 | 集中在 `application/services/`，职责清晰 |
| 基础设施文件数 | 分散 | 集中在 `infrastructure/`，实现端口 |
| God Class (>900 行) | 3+ | 0 |
| 最大文件行数 | 964 | ≤400 |
| 职责重复（同名子包） | 多处（execution、market 等） | 消除（仅 infrastructure 保留实现） |
| 架构合规性 | 违规多处 | 四层依赖单向（经自动化验证） |
| 新人上手成本 | 高（概念混乱） | 低（清晰分层） |

## 风险与对策

| 风险 | 对策 |
|------|------|
| 重构导致行为改变 | 每步骤前后都有测试基线；采用 TDD 方式：先保证测试通过，再重构，确保测试仍通过 |
| 大规模搬迁导致导入路径断裂 | 使用 IDE 重构工具；逐文件搬迁并立即测试；保留旧路径的 shim 期间过渡（若必须） |
| 团队成员不熟悉新结构 | 编写迁移指南；在代码评审中强调新结构；首次合并后进行知识分享会 |
| 性能下降（因更多抽象层） | 保持同样实现；仅改变代码组织；性能基准测试前后对比确保无显著下降 |

## 后续工作
- 在此基础上进行微服务拆分（如有需要）
- 实现领域事件驱动架构（如有需要）
- 引入 CQRS 以进一步分离读写路径
- 持续监控架构合规性（可通过架构单元测试自动检查）

## 结束语
本次重构旨在恢复架构的概念完整性，使代码库再次符合其声明的四层结构和 SOLID 原则。通过消除职责重复与神类，我们将获得更易维护、更易测试、更易于协作的代码库。

---

**设计完成时间**：2026-06-28  
**设计者**：CSO 安全审计后续架构重构小组  
**相关任务**：  
- 编写此设计文档（本文件）  
- 下一步：使用 `writing-plans` 技能创建详细的实施计划  

**备注**：本设计在得到批准后将进入实施阶段。