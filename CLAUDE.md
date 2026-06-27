# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Quant Atlas** is an intelligent retail investment research platform with:
- Data feeds: TDX, yfinance, AkShare
- Backtesting engine supporting 40+ strategy models
- Chart display, stock selection, watchlist features
- Multi-agent research (LangGraph-based research in `app/agents/research`)

## Tech Stack

- **Language**: Python 3.10+
- **Web**: Flask, Flask-Login
- **DB**: SQLAlchemy (MySQL/PostgreSQL support)
- **Cache**: Redis
- **Task Queue**: Celery
- **Format linting**: Ruff
- **Type checking**: Mypy
- **Test framework**: Pytest

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install with optional dependencies
pip install -r requirements.txt[celery,qlib,rdagent]

# Run tests
pytest

# Run single test
pytest tests/path/test_module.py::test_name

# Lint/format
ruff check .
ruff format .

# Type check
mypy app/

# Start dev server
# (See app/README.md for bootstrap)
```

## Architecture Overview

### Four-Layer Vertical Structure (Top-down dependencies)

| Layer | Path | Responsibility | Allowed Dependencies |
|-------|------|---------------|---------------------|
| **Presentation** | `presentation/web`, `presentation/api`, `presentation/routes` | HTTP, templates, JSON, route registration, Flask-Login session model | `application`, `domain`, `config`; never direct `infrastructure` or business rules |
| **Application** | `application/services` | Use-case orchestration, transaction boundary, permission & validation entry points | `domain` (entities/ports/enums); calls infrastructure via **ports** only |
| **Domain** | `domain` | Entities, value objects, enums, `ports` interfaces, role directories, analysis logic | Standard library / typing only; **no** `infrastructure` / `presentation` |
| **Infrastructure** | `infrastructure` | Port implementations: repositories, external APIs, TDX, Qlib, messages, adapters | `domain`; **no** `presentation` |
| **Cross-cutting** | `core`, `config` | Logging, factories, config, utility functions | Minimal dependencies as needed |
| **Tasks** | `tasks` | Celery tasks: composition of application services & infrastructure | Same as application layer |

### Key Architectural Principles (SOLID)

1. **SRP** (Single Responsibility): Each module/class has one clear reason to change
2. **OCP** (Open/Closed): Extension over modification; new capabilities via ports/registry
3. **LSP** (Liskov Substitution): Subtypes/alternatives must be losslessly swapable
4. **ISP** (Interface Segregation): Domain ports keep contracts minimal
5. **DIP** (Dependency Inversion): Application layer depends only on `domain.ports`
6. **LoD** (Demeter): Minimize cross-object chaining; interact only with direct collaborators

### Unified Tool Facade (2026-04-25 refactor)

The `ToolFacadeService` consolidates these capabilities:
- `MarketDataAccess` → fetch market data
- `FundamentalDataAccess` → fundamental data
- `StockNewsAccess` → news
- `StrategyToolBridge` → backtest/stock selection bridge

**Usage**:
```python
from app.application.services.tool_facade_service import ToolFacadeService
# Inject market_provider, stock_service, archive, fundamental_provider, strategy_service
facade = ToolFacadeService(...)
bars, note = facade.fetch_bars("600519", MarketCode.CN)
```

**Deprecated** (still compatible):
```python
from app.services.data import MarketDataAccess  # DeprecationWarning
```

### API Versioning Strategy

| Version | Path | Features |
|---------|------|----------|
| v1 | `/api/v1/*` | Traditional format, existing clients |
| v2 | `/api/v2/*` | DTO validation, standardized response `{ok, data, meta}` |

### Market Coverage

- A 股 (.SH/.SZ), 港股 (.HK), 美股，Crypto

## Domain-Driven Design

The `domain/ports.py` file defines interface contracts:
```python
class ToolFacadePort(Protocol):
    def fetch_bars(self, symbol: Symbol, market: MarketCode) -> ...
    def ...  # other contracts
```

Infrastructure layers implement these ports (e.g., `infrastructure/repositories/`).

## Coding Standards

- Source files use UTF-8; Python follows PEP 8
- Use type hints (`typing` / builtins generics)
- Public APIs & cross-module boundaries must have clear signatures with brief docs
- Logging uses project's `logging` / `get_logger`; avoid `print` in production paths
- Catch exceptions at boundary layers and convert to clear semantics; never swallow
- Match existing style in `app/`; avoid meaningless abbreviations
- Control cyclomatic complexity; prefer early returns & small functions

## Agent Rules (Quant & LangGraph)

- All tools use `@tool` decorator; return Pydantic v2 models including `evidence` and `confidence` fields
- Prioritize calling existing user data & backtest services
- Preserve TradingAgents' debate mechanism and Supervisor
- Use type hints, async where I/O-bound, structured output

## Cross-Cutting Conventions

- **Logging**: Use `get_logger(__name__)` pattern, configure at bootstrap
- **Database**: See `docs/DATABASE_GUIDE.md`; `infrastructure/database/` for ORM models
- **Repos**: See `docs/refactor/repositories-layout.md`

## Files to Read Before Starting

- [Architecture](app/README.md) — Directory structure, layers, DDD pattern
- [Platform Manual](docs/QUANT_ATLAS_平台手册.md) — End-to-end overview
- [Refactoring Log](REFACTORING_LOG.md) — Recent structural changes
- [Cursor Rules](.cursorrules) — Agent-specific guidelines

## Development Workflow

1. Read `app/README.md` for layer diagram & API strategy
2. Check `REFACTORING_LOG.md` for recent refactor context
3. For new capabilities: implement port in `domain/`, then infrastructure
4. Use Ruff + mypy for code quality; pytest for verification

## Notes

- **Change log requirement**: All behavioral/contract/data-format/deployment changes must be recorded in `REFACTORING_LOG.md` with date; do not just modify code without documentation
- **TradingAgents** (in separate `TradingAgents-CN` subdirectory) has its own package `tradingagents`; research agents in `app/agents/research` don't depend on it

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（20 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令

## 可用 Skills

Skills 位于 `.claude/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文 review 沟通参考——话术模板、分级标注（必须修复/建议修改/仅供参考）、国内团队常见反模式应对。仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。
- **chinese-commit-conventions**: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配、commitlint/husky/commitizen 中文模板、conventional-changelog 中文配置。仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。
- **chinese-documentation**: 中文文档排版参考——中英文空格、全半角标点、术语保留、链接格式、中文文案排版指北约定。仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。
- **chinese-git-workflow**: 国内 Git 平台配置参考——Gitee、Coding.net、极狐 GitLab、CNB 的 SSH/HTTPS/凭据/CI 接入差异与镜像同步配置。仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发，或在执行实现计划之前使用——通过原生工具或 git worktree 回退机制确保隔离工作区存在
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `Skill` 工具加载对应 skill 并严格遵循其流程。绝不要用 Read 工具读取 SKILL.md 文件。

如果你认为哪怕只有 1% 的可能性某个 skill 适用于你正在做的事情，你必须调用该 skill 检查。

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec

## gstack — AI Software Factory

This project has **gstack** installed — an open-source software factory by Garry Tan (YC CEO) that turns Claude Code into a virtual engineering team with 55 opinionated slash-command skills.

### Core Workflow

**Think → Plan → Build → Review → Test → Ship → Reflect**

### Key Skills

| Category | Commands | Purpose |
|----------|----------|---------|
| **Product** | `/office-hours`, `/spec` | Frame the problem, challenge assumptions, scope |
| **Planning** | `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/plan-devex-review` | CEO/Eng/Design/DevEx review before writing code |
| **Design** | `/design-consultation`, `/design-shotgun`, `/design-html`, `/design-review` | Full design system research, mockups, HTML |
| **Code Review** | `/review`, `/codex`, `/qa` | Bug detection, cross-model review, browser QA |
| **Shipping** | `/ship`, `/land-and-deploy`, `/canary` | Tests, coverage, PR, deploy, post-deploy monitoring |
| **Security** | `/cso`, `/careful`, `/freeze`, `/guard` | Threat modeling, destructive command safety |
| **Debugging** | `/investigate` | Systematic root-cause debugging |
| **Docs** | `/document-generate`, `/document-release`, `/make-pdf`, `/diagram` | Diataxis framework, release notes, PDFs |
| **Retro** | `/retro`, `/learn` | Sprint retrospectives, cross-session learning |

### Available gstack Skills (55 total)

`/gstack-upgrade`, `/autoplan`, `/benchmark`, `/benchmark-models`, `/browse`, `/canary`, `/careful`, `/codex`, `/context-restore`, `/context-save`, `/cso`, `/design-consultation`, `/design-html`, `/design-review`, `/design-shotgun`, `/devex-review`, `/diagram`, `/document-generate`, `/document-release`, `/freeze`, `/guard`, `/health`, `/investigate`, `/ios-clean`, `/ios-design-review`, `/ios-fix`, `/ios-qa`, `/ios-sync`, `/land-and-deploy`, `/landing-report`, `/learn`, `/make-pdf`, `/office-hours`, `/open-gstack-browser`, `/pair-agent`, `/plan-ceo-review`, `/plan-design-review`, `/plan-devex-review`, `/plan-eng-review`, `/plan-tune`, `/qa`, `/qa-only`, `/retro`, `/review`, `/scrape`, `/setup-browser-cookies`, `/setup-deploy`, `/setup-gbrain`, `/ship`, `/skillify`, `/spec`, `/sync-gbrain`, `/unfreeze`

### How to Use

- Start a new idea with: `/office-hours` or `/spec`
- Review existing code with: `/qa` or `/review`
- Ship a feature with: `/ship`
- Debug a production issue with: `/investigate`
- Security audit with: `/cso`
- For full details: invoke `/gstack` or read `~/.claude/skills/gstack/SKILL.md`
