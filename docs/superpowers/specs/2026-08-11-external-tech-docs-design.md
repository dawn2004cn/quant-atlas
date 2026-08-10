# 对外技术文档门户设计

> 日期：2026-08-11  
> 状态：待用户审阅 spec  
> 范围：两者兼顾——开源贡献者 + 接入方/合作伙伴；内部文档降级不外链

## 1. 背景

`docs/` 现存 250+ Markdown：编号体系（01–05）、平台手册、ADR、以及大量内部 plan/审计/midify。  
根 `README.md` 仍描述旧前端栈，对外读者难以找到「可承诺」的技术说明。

**目标：** 建立精简、稳定、可对外发布的技术文档门户，与内部工作文档分离。

## 2. 方案选择

采用已确认的 **方案 B：新建 `docs/public/` 精简集**。

- 不采用 A（仅改索引）——无法隔离内部噪音  
- 不采用 C（全量搬家）——范围过大  

## 3. 受众与阅读路径

| 受众 | 入口路径 |
|------|----------|
| 首次接触 | 仓库 `README.md` → `docs/public/01-overview.md` |
| 本地开发 / 贡献 | `03-getting-started` → `02-architecture` → `07-contributing` |
| API 接入 / 合作方 | `04-api` → OpenAPI / 公开路径列表 |
| 策略扩展 | `05-strategy-sdk` |
| 运维部署 | `06-deployment` |

## 4. 目录与文件

新建：`docs/public/`

| 文件 | 职责 |
|------|------|
| `README.md` | 对外门户首页：导航表、角色路径、与内部文档边界说明 |
| `01-overview.md` | 产品定位、Quant OS 五层、市场覆盖、明确不做 |
| `02-architecture.md` | 分层、14 模块、Registry/DI；对齐 `app/README.md`（精简版） |
| `03-getting-started.md` | Python 版本、安装、启动、SPA `/app`、健康检查 |
| `04-api.md` | v1/v2、鉴权概要、公开路径、稳定性分级、OpenAPI 指针 |
| `05-strategy-sdk.md` | Strategy SDK 生命周期、示例、主要 API；提炼现有 SDK 文档 |
| `06-deployment.md` | 部署轮廓、关键环境变量类别、不写密钥明文 |
| `07-contributing.md` | 分支约定、测试/lint、分层约束、插件贡献入口 |

更新：

| 文件 | 变更 |
|------|------|
| 仓库根 `README.md` | 修正技术栈（Flask + React SPA）；文档表指向 `docs/public/` |
| `docs/README.md` | 顶部「对外」区块 + 「内部（不对外部承诺）」区块 |

## 5. 写作原则

1. **可承诺事实优先**：架构、启动、API 约定、SDK 契约  
2. **不外链内部噪音**：`docs/superpowers/plans`、审计白皮书、midify_* 不进 public 导航  
3. **中文为主**，专有名词保留英文（API、SDK、Registry、Quant OS）  
4. **短文 + 深链**：不整本复制平台手册；需要处链到 `app/README.md`、`docs/API_ROUTE_CONTRACT.md`（标注「工程细节」）  
5. **无密钥**：部署章只列变量名与用途类别  

## 6. 明确不做（本轮）

- 不上 MkDocs / Docusaurus 站点  
- 不删除历史 plan / 审计文件  
- 不重写 OpenAPI 全量生成流水线（只指针现有 `docs/openapi.json` 若可用）  
- 不把 Wave2 未稳定能力写成对外 SLA  

## 7. 验收标准

- [ ] `docs/public/` 8 个文件齐全且互相链接正确  
- [ ] 根 `README.md` 与 `docs/README.md` 已区分对外/内部  
- [ ] 抽查：public 内无「midify」「审计白皮书」式内部计划全文粘贴  
- [ ] 技术栈描述与当前 SPA（`/app`）一致  

## 8. 实现顺序（批准后）

1. 写本 spec（本文件）并获审阅通过  
2. writing-plans → 短计划  
3. 按文件产出 `docs/public/*`，更新两个 README，提交 PR  
