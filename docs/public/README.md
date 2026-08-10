# Quant Atlas 对外技术文档

面向 **开源贡献者 / 二次开发者** 与 **接入方 / 合作伙伴** 的可承诺技术说明。

内部计划、审计、重构草案见仓库 `docs/` 其他目录，**不作为对外契约**。

## 阅读路径

| 你是谁 | 建议顺序 |
|--------|----------|
| 第一次了解产品 | [01 概览](./01-overview.md) |
| 本地跑起来 / 贡献代码 | [03 快速开始](./03-getting-started.md) → [02 架构](./02-architecture.md) → [07 贡献指南](./07-contributing.md) |
| 对接 API | [04 API](./04-api.md) |
| 扩展策略 / 用 SDK | [05 SDK 与策略扩展](./05-strategy-sdk.md) |
| 部署运维 | [06 部署](./06-deployment.md) |

## 文档列表

| 文档 | 内容 |
|------|------|
| [01-overview.md](./01-overview.md) | 定位、能力边界、市场覆盖 |
| [02-architecture.md](./02-architecture.md) | 分层、模块、DI |
| [03-getting-started.md](./03-getting-started.md) | 安装与启动 |
| [04-api.md](./04-api.md) | API 版本、鉴权、公开路径 |
| [05-strategy-sdk.md](./05-strategy-sdk.md) | `app.sdk` 与扩展约定 |
| [06-deployment.md](./06-deployment.md) | 部署轮廓与配置类别 |
| [07-contributing.md](./07-contributing.md) | 贡献与质量门禁 |

## 与内部文档的边界

- **对外（本目录）**：可承诺的架构事实、启动方式、API 约定、贡献流程  
- **内部**：`docs/superpowers/`、各类 `*plan*`、审计白皮书、会话日志 — 不对外部 SLA / 稳定性做承诺  

工程细节深链（可选）：[`app/README.md`](../../app/README.md)、[`docs/API_ROUTE_CONTRACT.md`](../API_ROUTE_CONTRACT.md)
