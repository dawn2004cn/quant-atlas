# ADR-0002: OpenAPI 工具选用 apispec + apispec-webframeworks

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §6（API 契约）

## 背景

Flask → SPA 迁移要给 110+ API 路由建立 OpenAPI 3.0 合同，前端通过 `openapi-typescript` 生成 TS 类型。要在两个候选工具之间选定：

| 选项 | 集成方式 | 工作量 |
|---|---|---|
| `apispec` + `apispec-webframeworks` | 在路由函数 docstring 里加 YAML 块，扫描时聚合成 spec | 渐进式，每个路由独立标注，零侵入 |
| `flask-smorest` | 把每个路由改成继承 `MethodView` 的类，schema 通过 marshmallow 自动生成 | 重构式，所有 110 路由都要改架构 |

## 决策

**采用 `apispec` + `apispec-webframeworks`**。

每个路由函数在 docstring 里用 YAML 描述 request / response schema，通过 `apispec` 扫描聚合成 `openapi.json`，Flask 用 `/openapi.json` 与 `/docs`（Swagger UI）两个端点暴露。

## 理由

1. **路由函数风格已确立**：项目 110 个路由都是 Flask 函数式装饰器路由（`@bp.route`），不是 class-based view。改 `flask-smorest` 要把每个路由改成 `MethodView` 类，是结构性重构。
2. **Karpathy 准则**：当前每个路由 docstring 加 10 行 YAML，是表面级渐进添加。改 view-class 是动整个项目的架构，违背"surgical changes"原则。
3. **pydantic v2 已就位**：项目 DTO 已用 pydantic v2，apispec 的 `apispec.ext.marshmallow` 是可选插件，不强制 marshmallow——可继续用 pydantic 加 `model_json_schema()` 自动生成 schema 喂给 apispec。
4. **迁移可逆**：apispec 标注是 docstring，不改函数签名，将来若发现 flask-smorest 优势更大可随时再切换，无沉没成本。

## 后果

### 正面
- 110 个路由可分批标注（M1/M2 每个新迁页面带上对应 API），不阻塞迁移节奏。
- docstring 即文档，函数签名零变更，新人易上手。
- `/openapi.json` + `/docs` 两个端点开发期可用，QA / 前端可直接试 API。

### 负面
- 多人维护时容易出现"schema 标注与代码不同步"——必须配 CI 检查（已在 M0 任务 8 `openapi-check` job 计划）。
- 嵌套 schema 复用要靠 `components/schemas` 手动管理，初期会有些重复（后期可抽 helper）。

### 中性
- `flask-smorest` 提供的"输入校验自动 400"功能，apispec 路径需要手动加 pydantic 校验装饰器（项目已有此模式）。

## 实施清单

- [ ] M0 任务 1：`pyproject.toml` 加 `apispec>=6.4`、`apispec-webframeworks>=1.0`
- [ ] M0 任务 4：建 `app/presentation/api/openapi_builder.py`，扫描所有蓝图生成 `openapi.json`
- [ ] M0 任务 4：注册 `/openapi.json` 与 `/docs`（Swagger UI 静态资源）路由
- [ ] M0 任务 4：选 3 个示范路由（auth/login、auth/refresh、stock/list）作为 docstring YAML 标注模板
- [ ] M0 任务 5：前端加 `openapi-typescript` devDep，生成 `frontend/src/api/types.ts`
- [ ] M0 任务 8：CI `openapi-check` job 跑 `python -m app.presentation.api.openapi_builder --check`，schema 漂移立即失败

## 替代方案为何被否

- **flask-smorest**：要求把 110 个路由全部改成 `MethodView` 类，工程量大、风险高，且 marshmallow 与项目现有 pydantic v2 DTO 体系冲突，需要重复定义 schema。
