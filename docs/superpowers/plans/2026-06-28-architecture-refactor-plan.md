# 架构重构实施计划：消除职责重复、神类与重复层

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 重构 Quant Atlas 架构以恢复清晰的四层结构，消除职责重复、God Classes 和重复层。

**架构：** 按阶段执行：0 准备 → 1 清理可见重复 → 2 Domain 净化 → 3 拆分 God Classes → 4 验证依赖 → 5 测试与质量 → 6 文档

**技术栈：** Python, Git, Pytest, IDE 重构工具, mypy, ruff

---

## 文件清单

### 将被删除的文件
- `app/services/` 整个目录（已标记废弃的兼容层）
- `app/application/facades/` 整个目录
- `app/domain/ports/` 整个目录（内容合并到 `app/domain/ports.py`）
- `app/facade/` 中除 shim 外的所有文件（在 shim 替换完成后）

### 将被创建的文件
- `app/application/facade/market_data_facade.py`（从 `app/application/facades/` 合并）
- 多个新的应用服务文件（从 domain/ 中搬出的服务）
- `app/infrastructure/repositories/mysql/mysql_tdx_dayk_read_repository.py`
- `app/infrastructure/repositories/mysql/mysql_tdx_dayk_write_repository.py`
- `app/infrastructure/repositories/mysql/mysql_tdx_dayk_migration_repository.py`
- `app/modules/system/services/institution_tier_query_service.py`
- `app/modules/system/services/institution_tier_update_service.py`
- `app/modules/system/services/institution_tier_validator.py`
- `app/models/trend_breakout_model.py`
- `app/models/trend_breakout_service.py`

### 将被修改的文件
- `app/domain/ports.py`（合并 domain/ports/ 的内容）
- `app/facade/__init__.py` 和每个 facade 文件（改为 shim）
- `app/application/facade/__init__.py`（添加入口）
- 各种测试文件（新增测试或修复遗漏测试）
- `docs/architecture/` 相关文档
- `REFACTORING_LOG.md`

---

### 任务 0：准备工作

**文件：**
- 创建：无
- 修改：无
- 测试：无

- [ ] **步骤 1：确保当前测试通过**

```bash
cd E:\project\workspace\myrepo\quant-atlas
pytest -q --no-header 2>&1 | tail -5
```

预期：输出显示 "N passed" 且无失败。如果失败，先修复现有问题。

- [ ] **步骤 2：创建开发分支**

```bash
git checkout -b architecture/refactor-v1
```

- [ ] **步骤 3：记录基线测试结果**

```bash
pytest --tb=short --no-header 2>&1 | tee /tmp/baseline-test-report.txt
```

- [ ] **步骤 4：提交基线状态**

```bash
git add -A && git commit -m "chore: set baseline for architecture refactor (refactor-v1)"
```

---

### 任务 1：删除 app/services/（已废弃兼容层）

**文件：**
- 删除：`app/services/` 整个目录

- [ ] **步骤 1：备份 app/services/ 内容（检查是否有任何引用）**

```bash
cd E:\project\workspace\myrepo\quant-atlas
grep -r "from app.services\|import app.services" app/ tests/ --include="*.py" 2>/dev/null | head -20
```

预期：如果有引用，记录它们。预期无大量引用，因为该目录已被标记为废弃。

如果发现任何引用，需要先迁移到新的导入路径再删除。

- [ ] **步骤 2：删除 app/services/ 目录**

```bash
git rm -r app/services/
```

- [ ] **步骤 3：运行测试验证删除未造成任何损坏**

```bash
pytest -q --no-header 2>&1 | tail -5
```

预期：与基线测试结果相同（测试数量和通过率一致）。

- [ ] **步骤 4：提交**

```bash
git add -A && git commit -m "refactor(arch): remove deprecated app/services/ compatibility layer"
```

---

### 任务 2：删除 app/application/facades/ 重复目录

**文件：**
- 删除：`app/application/facades/` 整个目录（注意：这里有一个 `s`，与 `app/application/facade/` 不同）

- [ ] **步骤 1：备份并检查 app/application/facades/ 的引用**

```bash
cd E:\project\workspace\myrepo\quant-atlas
find app/application/facades/ -name "*.py" 2>/dev/null
grep -r "from app.application.facades\|from app.application.facades" app/ tests/ --include="*.py" 2>/dev/null | head -20
```

- [ ] **步骤 2：迁移内容（若有的话）**

如果 `app/application/facades/` 中的文件与 `app/application/facade/` 不同，先将其合并到唯一的 `app/application/facade/` 目录。

```python
# 例如，app/application/facades/market_data_facade.py → app/application/facade/market_data_facade.py
# 并在旧位置保留 shim
```

- [ ] **步骤 3：删除 app/application/facades/**

```bash
git rm -r app/application/facades/
```

- [ ] **步骤 4：运行测试验证**

```bash
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 5：提交**

```bash
git add -A && git commit -m "refactor(arch): remove duplicate app/application/facades/ directory"
```

---

### 任务 3：统一端口定义

**文件：**
- 修改：`app/domain/ports.py` — 合并 `app/domain/ports/` 的内容
- 删除：`app/domain/ports/` 目录

- [ ] **步骤 1：检查 app/domain/ports/ 目录内容**

```bash
cd E:\project\workspace\myrepo\quant-atlas
find app/domain/ports -name "*.py" ! -name "__init__.py" 2>/dev/null | sort
```

- [ ] **步骤 2：检查当前 app/domain/ports.py 内容**

读取 `app/domain/ports.py`，记录现有端口类（如 `VectorSearchServicePort`，`ToolFacadePort`）。

- [ ] **步骤 3：合并 port 子包内容到 ports.py**

对于 `app/domain/ports/` 中每个有用的端口类，将其导入到 `app/domain/ports.py` 中，按需添加类。确保保留所有现有 API。

```python
# 在 app/domain/ports.py 末尾追加
# 来自 domain/ports/ 的导出
from app.domain.ports.<module> import <PortClass>
```

- [ ] **步骤 4：检查是否有导入引用 app/domain/ports/**

```bash
grep -r "from app.domain.ports\.\|import app.domain.ports\." app/ tests/ --include="*.py" 2>/dev/null | grep -v "ports.py" | head -40
```

- [ ] **步骤 5：删除 app/domain/ports/ 目录**

```bash
git rm -r app/domain/ports/
```

- [ ] **步骤 6：运行测试验证**

```bash
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 7：提交**

```bash
git add -A && git commit -m "refactor(arch): consolidate port definitions into domain/ports.py"
```

---

### 任务 4：清理 app/facade/（改为 shim）

**文件：**
- 修改：`app/facade/` 中的每个文件改为 shim（单行导入）

- [ ] **步骤 1：检查 app/facade/ 的引用**

```bash
cd E:\project\workspace\myrepo\quant-atlas
grep -r "from app.facade\|import app.facade" app/ tests/ --include="*.py" 2>/dev/null | head -30
```

- [ ] **步骤 2：确认 app/application/facade/ 中有对应的文件**

```bash
ls app/application/facade/
ls app/facade/
```

每个 `app/facade/*.py` 中对应的功能应该能在 `app/application/facade/` 中找到。

- [ ] **步骤 3：将每个 app/facade/*.py 改为 shim**

```python
# app/facade/market_facade.py 改为：
"""
Shim 导入 — 优先使用 from app.application.facade.market_facade import ...
"""
from app.application.facade.market_facade import *  # noqa: F401, F403
from app.application.facade.market_facade import __all__  # noqa: F401

import warnings
warnings.warn(
    "import from app.facade is deprecated; use app.application.facade instead",
    DeprecationWarning,
    stacklevel=2,
)
```

- [ ] **步骤 4：运行测试验证 shim 过渡正常工作**

```bash
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 5：提交**

```bash
git add -A && git commit -m "refactor(arch): convert app/facade/ to shim, redirect to app.application.facade"
```

---

### 任务 5：Domain 净化 — 搬迁应用服务（批次 B1）

**文件：**
- 修改：多个（在 domain/services/、domain/workflow*/ 中的应用服务 → 搬迁到 application/services/）
- 修改：相关引用

- [ ] **步骤 1：扫描 domain/ 中的 services 内容**

```bash
cd E:\project\workspace\myrepo\quant-atlas
ls -la app/domain/services/
find app/domain -name "*service*" -o -name "*workflow*" | grep -v __pycache__ | sort
```

确认每个文件的类型：
- 纯领域实体/值对象（无外部依赖）→ 保留
- 应用服务（有外部依赖、编排逻辑）→ 搬迁到 `application/services/`
- 基础设施逻辑（DB 访问、网络调用）→ 搬迁到 `infrastructure/`

- [ ] **步骤 2：搬迁第一个识别出的服务**

例如，如果 `app/domain/services/task_service.py` 是一个应用服务：

```bash
mkdir -p app/application/services/domain_migrations/
git mv app/domain/services/task_service.py app/application/services/domain_migrations/
```

- [ ] **步骤 3：更新引用**

```bash
# 搜索旧路径引用
grep -r "from app.domain.services.task_service\|from app.domain.services import" app/ --include="*.py" 2>/dev/null
# 替换为新的路径（使用 git grep）
```

- [ ] **步骤 4：运行测试验证搬迁未造成损坏**

```bash
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 5：对 domain/ 中每个可识别的应用程序服务重复步骤 2-4**

逐一处理每个文件，避免一次处理过多导致调试困难。预期搬迁 5-15 个文件。

- [ ] **步骤 6：整体提交**

```bash
git add -A && git commit -m "refactor(arch): migrate application services from domain/ to application/services/"
```

---

### 任务 6：Domain 净化 — 检查并搬迁带外部依赖的分析模块（批次 B2）

**文件：**
- 检查：`app/domain/analysis/` 和 `app/domain/*/analysis*`
- 搬迁：有外部依赖的分析模块 → `application/services/`

- [ ] **步骤 1：扫描 domain/ 中的分析模块**

```bash
cd E:\project\workspace\myrepo\quant-atlas
find app/domain -path "*analysis*" -name "*.py" | grep -v __pycache__ | sort
```

- [ ] **步骤 2：检查每个文件是否有外部依赖**

对每个文件，读取其 `import` 语句确认依赖：
```bash
head -20 app/domain/analysis/some_module.py
grep "^from\|^import" app/domain/analysis/some_module.py
```

- 如果仅 `typing`, `enum`, `dataclasses`, `abc`, `datetime` → 保留在 domain/
- 如果 `sqlalchemy`, `requests`, `flask`, `redis`, `app.infrastructure` → 搬迁到 `application/services/`

- [ ] **步骤 3：搬迁带外部依赖的模块**

```bash
git mv app/domain/analysis/<module>.py app/application/services/
```

- [ ] **步骤 4：更新引用并运行测试**

```bash
grep -r "from app.domain.analysis." --include="*.py" app/ 2>/dev/null | head -10
# 更新这些引用为新的路径
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 5：提交**

```bash
git add -A && git commit -m "refactor(arch): migrate analysis modules with external deps from domain/ to application/"
```

---

### 任务 7：拆分 God Class — institution_tier_service.py（964行）

**文件：**
- 创建：`app/modules/system/services/institution_tier_query_service.py`
- 创建：`app/modules/system/services/institution_tier_update_service.py`
- 创建：`app/modules/system/services/institution_tier_validator.py`
- 修改：`app/modules/system/services/institution_tier_service.py`（瘦身为主入口/门面）

- [ ] **步骤 1：备援地创建测试基线**

```bash
cd E:\project\workspace\myrepo\quant-atlas
# 查找该文件的现有测试
find tests -name "*institution*" 2>/dev/null
```

如果无测试，创建基线：
```python
# tests/modules/system/test_institution_tier_query_service.py
"""InstitutionTierQueryService 单元测试。"""
```

- [ ] **步骤 2：阅读 institution_tier_service.py**

理解主要职责，列出所有方法并按以下类别分组：
1. 只读查询（get_by_id, list, find, search 等）
2. 写入/更新（create, update, delete, activate 等）
3. 业务规则校验（validate, check, verify 等）
4. 工具方法（helper, factory 等）

- [ ] **步骤 3：创建只读查询服务**

```python
# app/modules/system/services/institution_tier_query_service.py
"""Institution tier read-only queries."""

from app.modules.system.services.institution_tier_service import (
    InstitutionTierService,
)

class InstitutionTierQueryService:
    """只读层 — 封装所有 get/list/search 操作。"""

    def __init__(self, service: InstitutionTierService):
        self._service = service

    def get_by_id(self, tier_id: int) -> dict | None:
        return self._service._fetch_one(tier_id)

    def list_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        return self._service._fetch_all(limit, offset)
```

- [ ] **步骤 4：创建写入服务**

```python
# app/modules/system/services/institution_tier_update_service.py
```

- [ ] **步骤 5：创建校验服务**

```python
# app/modules/system/services/institution_tier_validator.py
```

- [ ] **步骤 6：瘦身原文件为门面**

```python
# app/modules/system/services/institution_tier_service.py — 瘦身版
"""Institution Tier Service — 统一入口，委托给各子服务。"""
from app.modules.system.services.institution_tier_query_service import InstitutionTierQueryService
from app.modules.system.services.institution_tier_update_service import InstitutionTierUpdateService
from app.modules.system.services.institution_tier_validator import InstitutionTierValidator

class InstitutionTierService:
    def __init__(self, ...):
        self.query = InstitutionTierQueryService(self)
        self.update = InstitutionTierUpdateService(self)
        self.validator = InstitutionTierValidator(self)
```

- [ ] **步骤 7：运行测试**

```bash
pytest -q --no-header -k "institution" 2>&1 | tail -5
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 8：提交**

```bash
git add -A && git commit -m "refactor(arch): split institution_tier_service.py into query/update/validator"
```

---

### 任务 8：拆分 God Class — trend_breakout.py（946行）

**文件：**
- 创建：`app/models/trend_breakout_model.py`
- 创建：`app/models/trend_breakout_service.py`
- 修改：`app/models/trend_breakout.py`（瘦身为门面或删除）

- [ ] **步骤 1：阅读 trend_breakout.py**

列出所有方法并按类别：纯计算（无外部依赖，仅 numpy/pandas）→ model；有外部依赖（数据库、API 调用）→ service。

- [ ] **步骤 2：创建纯模型**

```python
# app/models/trend_breakout_model.py
"""纯趋势突破模型 — 仅包含数据结构和纯计算。"""
```

将趋势突破算法、数据结构、校验等搬运到这里。

- [ ] **步骤 3：创建业务服务**

```python
# app/models/trend_breakout_service.py
"""趋势突破业务逻辑 — 包含外部依赖的操作。"""
```

将数据获取、持久化、缓存等搬运到这里。

- [ ] **步骤 4：原文件改为 shim/门面**

- [ ] **步骤 5：运行测试验证**

```bash
pytest -q --no-header -k "trend_breakout\|trend" 2>&1 | tail -5
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 6：提交**

```bash
git add -A && git commit -m "refactor(arch): split trend_breakout.py into model and service"
```

---

### 任务 9：拆分 God Class — mysql_tdx_dayk_repository.py（901行）

**文件：**
- 创建：`app/infrastructure/repositories/mysql/mysql_tdx_dayk_read_repository.py`
- 创建：`app/infrastructure/repositories/mysql/mysql_tdx_dayk_write_repository.py`
- 创建：`app/infrastructure/repositories/mysql/mysql_tdx_dayk_migration_repository.py`
- 修改：`app/infrastructure/repositories/mysql/mysql_tdx_dayk_repository.py`

- [ ] **步骤 1：阅读源文件，列出方法并归类

类似任务 7：按只读、写入、Schema 迁移分组。

- [ ] **步骤 2：创建读仓储**

```python
# app/infrastructure/repositories/mysql/mysql_tdx_dayk_read_repository.py
"""日K数据读操作。"""
```

- [ ] **步骤 3：创建写仓储**

```python
# app/infrastructure/repositories/mysql/mysql_tdx_dayk_write_repository.py
"""日K数据写操作。"""
```

- [ ] **步骤 4：创建迁移仓储**

```python
# app/infrastructure/repositories/mysql/mysql_tdx_dayk_migration_repository.py
"""日K数据 Schema 迁移。"""
```

- [ ] **步骤 5：原文件改为门面，代理到三个子仓储**

- [ ] **步骤 6：运行测试**

```bash
pytest -q --no-header -k "tdx_dayk\|tdx" 2>&1 | tail -5
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 7：提交**

```bash
git add -A && git commit -m "refactor(arch): split mysql_tdx_dayk_repository.py into read/write/migration repos"
```

---

### 任务 10：分层依赖验证

**文件：**
- 修改：必要时修改违规导入

- [ ] **步骤 1：运行现有的 cross-import gate（如果有）**

```bash
cd E:\project\workspace\myrepo\quant-atlas
python scripts/check_module_cross_imports.py 2>&1 || echo "No gate script exists"
```

- [ ] **步骤 2：手动检查 domain/ 是否有违规导入**

```bash
grep -r "^from app.infrastructure\|^import app.infrastructure\|^from app.application\|^from app.presentation" app/domain/ --include="*.py" 2>/dev/null
```

如果有违规，记录并修复。

- [ ] **步骤 3：手动检查 application/ 是否有违规导入**

```bash
grep -r "^from app.infrastructure\|^import app.infrastructure" app/application/ --include="*.py" 2>/dev/null
```

如果有违规（除了通过 ports 注入外），记录并修复。

- [ ] **步骤 4：修复发现的违规**

对于每处违规，将导入改为通过端口（ports）访问，或将代码移到正确的层。

- [ ] **步骤 5：提交修复**

```bash
git add -A && git commit -m "refactor(arch): fix layer dependency violations"
```

---

### 任务 11：补充测试（阶段 5）

**文件：**
- 创建：为每个拆分/搬迁的文件创建相应的测试文件
- 测试：`tests/` 目录

- [ ] **步骤 1：为每个新创建的模块编写测试**

目标：每个新建文件至少 80% 行覆盖率，覆盖主要业务路径。

对 `app/modules/system/services/institution_tier_query_service.py`：
```python
# tests/modules/system/test_institution_tier_query_service.py
"""InstitutionTierQueryService 单元测试。"""

import pytest
from app.modules.system.services.institution_tier_query_service import InstitutionTierQueryService

class TestInstitutionTierQueryService:
    def test_get_by_id_returns_none_when_not_found(self):
        ...
    def test_list_all_returns_empty_when_no_data(self):
        ...
```

对 `app/models/trend_breakout_model.py`：
```python
# tests/models/test_trend_breakout_model.py
"""TrendBreakoutModel 纯模型测试。"""
```

对 `app/infrastructure/repositories/mysql/test_mysql_tdx_dayk_read_repository.py`：
```python
# tests/infrastructure/repositories/mysql/test_mysql_tdx_dayk_read_repository.py
"""日K 读仓储测试（使用纯测试数据，避免外部依赖）。"""
```

- [ ] **步骤 2：运行全部测试验证无回归**

```bash
pytest -q --no-header 2>&1 | tail -5
```

- [ ] **步骤 3：提交测试**

```bash
git add -A && git commit -m "test(arch): add unit tests for refactored modules"
```

---

### 任务 12：文档与交付（阶段 6）

**文件：**
- 修改：`docs/architecture/` 相关文档
- 修改：`REFACTORING_LOG.md`

- [ ] **步骤 1：更新架构文档**

更新 `docs/architecture/` 或相关文档，反映新结构：
- 删除不再存在的路径（app/services/、app/domain/ports/ 等）
- 更新目录描述以匹配实际结构

- [ ] **步骤 2：更新 REFACTORING_LOG.md**

在末尾追加一条新的记录，总结本次重构的变更：
- 删除了哪些文件/目录
- 搬迁了哪些文件
- 拆分了哪些 God Class
- 预期的维护性收益

- [ ] **步骤 3：运行最终测试确认一切正常**

```bash
pytest -q --no-header 2>&1 | tail -5
git status
```

- [ ] **步骤 4：提交文档变更**

```bash
git add -A && git commit -m "docs(arch): update architecture docs and REFACTORING_LOG for refactor"
```

---

## 执行顺序

```
任务 0 (准备) → 任务 1 (清理 services/) → 任务 2 (清理 facades/) → 任务 3 (统一 ports) → 任务 4 (facade shim) → 任务 5 (domain 净化 B1) → 任务 6 (domain 净化 B2) → 任务 7 (God Class 1) → 任务 8 (God Class 2) → 任务 9 (God Class 3) → 任务 10 (依赖验证) → 任务 11 (补充测试) → 任务 12 (文档)
```

注：任务 1 到 4 可以有序执行（每个是独立的目录删除/合并），任务 5 和 6 可以并行，任务 7-9 可以并行。