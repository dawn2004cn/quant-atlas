# Quant-Atlas 文档中心

## 对外技术文档（推荐入口）

面向贡献者与接入方的可承诺说明：

**→ [`docs/public/`](./public/README.md)**

| 文档 | 内容 |
|------|------|
| [01 概览](./public/01-overview.md) | 定位与边界 |
| [02 架构](./public/02-architecture.md) | 分层与模块 |
| [03 快速开始](./public/03-getting-started.md) | 安装启动 |
| [04 API](./public/04-api.md) | 契约与鉴权 |
| [05 SDK](./public/05-strategy-sdk.md) | 可编程扩展 |
| [06 部署](./public/06-deployment.md) | 部署轮廓 |
| [07 贡献](./public/07-contributing.md) | 贡献流程 |

---

## 内部文档（不对外部承诺）

以下目录与文件供团队演进、审计与排期使用，**不构成对外 SLA / API 稳定性承诺**：

| 区域 | 说明 |
|------|------|
| [`01_Requirements/`](./01_Requirements/) 等编号目录 | 历史需求与设计整理 |
| [`superpowers/`](./superpowers/) | Agent 规格与实现计划 |
| [`adr/`](./adr/) | 架构决策记录 |
| [`audit/`](./audit/) 与各类审计白皮书 | 内部审计 |
| `*plan*`、`midify_*`、会话日志 | 过程文档 |
| [`API_ROUTE_CONTRACT.md`](./API_ROUTE_CONTRACT.md) | 工程契约（可被对外 API 文深链） |
| [`QUANT_ATLAS_平台手册.md`](./QUANT_ATLAS_平台手册.md) | 长篇平台手册（内部详述） |

### 历史「核心文档」索引（内部）

| 编号 | 文档 | 说明 |
| :--- | :--- | :--- |
| 01 | [需求分析](./01_Requirements.md) | 战略与需求（若文件存在） |
| 02 | [架构设计](./02_Architecture.md) | 内部架构叙述 |
| 03 | [功能手册](./03_Functional.md) | 功能详述 |
| 04 | [测试方案](./04_Testing.md) | 测试策略 |
| 05 | [部署指南](./05_Deployment.md) | 内部部署笔记 |
| 06 | [演进指南](./06_Expert_Evolution_Guide.md) | 产品演进 |

对外请优先使用 **`docs/public/`**，避免从本表直接外传。
