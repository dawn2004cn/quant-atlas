# 04 · API 指南

## 版本策略

| 版本 | 前缀 | 特点 |
|------|------|------|
| **v1** | `/api/v1/*` | 平台主 API；大量路由；部分接口支持服务降级响应 |
| **v2** | `/api/v2/*` | 更强 DTO 校验；推荐新集成使用标准化 envelope |

v2 成功响应常见形状：

```json
{ "ok": true, "data": {}, "meta": {} }
```

v1 历史客户端可能仍使用 `success` / `ok` 并存字段；新代码请以各路由实际返回为准，并以契约测试为准。

## 鉴权

| 方式 | 适用 |
|------|------|
| Flask-Login Session | Web / SPA Cookie 会话 |
| JWT（v2 auth） | `/api/v2/auth/token` 等机器集成 |

除下文**公开路径**外，默认需要登录会话或有效 Token。

## 公开路径（无需登录，只读）

代码权威列表：`app/presentation/api/public_api_paths.py`

| 路径 | 用途 |
|------|------|
| `GET /api/v1/health` | 存活探针 |
| `GET /api/v1/system/health` | 部署状态与能力摘要 |
| `GET /api/v1/compliance/manifest` | 合规文案 |

`system/health` 中 `status` 表示进程可服务；`deployment_status` 反映必需服务是否齐全。

## 稳定性分级（对外沟通建议）

| 级别 | 含义 | 示例 |
|------|------|------|
| **Stable** | CI 契约门禁覆盖，语义变更需公告 | 公开 health、核心回测/任务路径（见契约表） |
| **Evolving** | 可用但字段可能增补 | 多数业务 v1 资源 |
| **Experimental** | 特性开关控制，可能下线 | Mesh / 部分 AI 实验页面对应 API |

契约与 CI 门禁详情（工程向）：[`docs/API_ROUTE_CONTRACT.md`](../API_ROUTE_CONTRACT.md)

## OpenAPI

仓库提供 [`docs/openapi.json`](../openapi.json) 作为参考产物；**以运行中路由与契约脚本为准**。生成/同步流程可能随版本演进，接入方勿假设每日自动刷新。

## 错误与降级

- 应用层错误应转换为明确 HTTP/业务码，避免静默吞掉  
- 部分 v1 路由使用 `@service_fallback`：依赖服务未就绪时返回「不可用」结构而非 500（便于 SPA 降级展示）

## 平台元数据示例

```http
GET /api/v1/platform/strategic-features
```

用于 SPA 导航/特性开关（是否要求登录以实际路由为准）。

## 下一步

- [SDK](./05-strategy-sdk.md)
- [贡献 / 契约测试](./07-contributing.md)
