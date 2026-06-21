# ADR-0001: JWT 签名算法选用 RS256

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §5.1（双轨认证）

## 背景

Flask → SPA 迁移期间要引入双轨认证（cookie 维持兼容 + JWT 为 SPA / Flutter 新增）。Flutter mobile 工程会在 M4 阶段接入同一套 JWT。我们要选定 access_token（5min）+ refresh_token（30d）的签名算法。

候选方案：

| 选项 | 优点 | 缺点 |
|---|---|---|
| HS256（HMAC + 共享密钥） | 单进程足够；配置简单（1 个 secret）；签发 / 验证零延迟 | 密钥泄露 = 全军覆没；跨服务分发密钥时风险扩散 |
| RS256（RSA 公私钥） | 公钥可分发，私钥只在 Flask；Flutter / 未来网关可独立验签；密钥轮换更平滑 | 多管 1 对密钥；签发耗时 ~10× HS256（仍为微秒级，可忽略） |

## 决策

**采用 RS256**。

私钥（PEM）由 Flask 进程持有，公钥（PEM 或 JWK 格式）可对外分发。token 中签名算法字段 `alg` 在签发与校验两侧均强制白名单匹配，禁止 `alg: none` 与 HS256 降级攻击。

## 理由

1. **多端异构客户端**：Flutter mobile 工程是异构客户端，未来可能在客户端独立验签（离线模式）、或交给 API 网关侧统一验签——只有非对称算法能在不泄露签名密钥的前提下做到。
2. **算法升级是破坏性变更**：HS256 → RS256 切换会让所有已发 token 立即失效。一次到位避免后续大动迁。
3. **性能差距可忽略**：签发耗时差异在微秒级，相比网络往返完全不显著。
4. **行业标准**：大型公有 OAuth2 / OIDC 实现（Auth0、Okta、Google Identity）默认 RS256，工具链生态成熟。

## 后果

### 正面
- 公钥可放在 `/.well-known/jwks.json` 之类端点公开，便于多端独立验签。
- 密钥轮换可通过 JWK Set 中保留多个 kid 实现平滑过渡。
- Flutter 端可用 Dart 的 `dart_jsonwebtoken` 包独立验签。

### 负面
- 必须管理私钥与公钥两份文件；密钥生成、存储、备份需要清晰流程。
- `PyJWT` 默认不含 RS256 依赖，必须装 `PyJWT[crypto]`，体积略增（cryptography ~ 5MB）。
- 部署时 secrets 管理流程要更新（私钥不能进代码仓 / 不能放 .env 明文）。

### 中性
- 签发性能差距在生产负载下不会成为瓶颈（access_token 5min 一签，refresh 30d 一签）。

## 实施清单

- [ ] M0 任务 1：`pyproject.toml` 加 `PyJWT[crypto]>=2.8`
- [ ] M0 任务 1：脚本生成 RSA 2048 位密钥对，私钥落到 `instance/keys/jwt-private.pem`（已 gitignore），公钥落到 `instance/keys/jwt-public.pem`
- [ ] M0 任务 1：`config/secret.cfg.example` 加 `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` 占位
- [ ] M0 任务 3：JWT 签发 / 校验工具函数强制 `algorithms=["RS256"]`，禁止 `alg: none`
- [ ] M0 任务 6：流式 SSE 一次性短期 token 也用 RS256（同一对密钥，无额外依赖）
- [ ] M4：暴露 `/.well-known/jwks.json` 端点供 Flutter / 网关使用

## 替代方案为何被否

- **HS256**：无法满足 Flutter 异构客户端独立验签的需求；将来要升级 RS256 时所有已发 token 立即失效，是破坏性变更，不如一次到位。
