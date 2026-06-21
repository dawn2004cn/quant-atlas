# ADR-0003: JWT 滑动续期 + Refresh Token Rotation

- **状态**：Accepted
- **日期**：2026-06-21
- **决策者**：项目负责人
- **关联里程碑**：M0（地基）
- **关联文档**：`docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md` §5.2（认证流程）
- **依赖 ADR**：[0001](0001-jwt-algorithm.md)（RS256 签名算法）

## 背景

JWT 双轨认证下 refresh_token（30d）的续期策略有两种典型选择：

| 选项 | 行为 | 用户体验 |
|---|---|---|
| 滑动续期（sliding） | 用户每次 refresh 时 refresh_token 也顺延，活跃用户永不掉线 | 看盘 / 下单流不中断 |
| 固定到期（fixed） | refresh_token 30d 死期到必须重新登录 | 30d 后强制中断 |

金融交易场景中，"看盘中突然弹登录框 → 错过下单时机"是高敏感故障。

## 决策

**采用滑动续期（sliding）+ Refresh Token Rotation**。

具体规则：

1. **滑动续期**：用户用 refresh_token 换 access_token 时，同时签发**新的 refresh_token**（exp 重新 30d 计时），旧 refresh_token 立即作废。
2. **Rotation**：每个 refresh_token 只能使用一次。一旦用过就加入 deny list（Redis，TTL 与原 token exp 对齐）。
3. **重放检测**：若同一 refresh_token 被使用第二次（说明被盗用），整条 token 链立即失效，强制该用户全设备重新登录，并在审计日志记录。
4. **绝对上限**：刷新链有绝对上限 90d（jti 链头记录初次签发时间），超过 90d 即使持续活跃也必须重新登录。防止失窃 token 永久续命。

## 理由

1. **业务场景敏感**：金融交易"看盘 → 决策 → 下单"是连续操作链，30d 强制中断会显著影响用户体验。
2. **Rotation 提供安全网**：单纯滑动续期会让失窃 refresh_token 永久续命；Rotation + 重放检测可在攻击者尝试第二次使用时立刻发现并掐断。
3. **行业最佳实践**：OAuth 2.1 草案明确推荐 refresh token rotation；Auth0、Okta 均默认开启。
4. **绝对上限兜底**：90d 硬上限确保即使失窃 token 已重放成功，攻击者最多用 90d，不会永久存在。

## 后果

### 正面
- 活跃用户永不掉线，下单流程零中断。
- 失窃 token 被重放使用时可立刻发现，安全性高于固定到期。
- 用户在多设备同时登录时，每个设备独立 jti 链，互不影响。

### 负面
- 必须有 Redis（或等价 KV 存储）维护 deny list，单 Flask 进程模式不可行——项目已用 Redis，无新依赖。
- Rotation 逻辑实现复杂度 +1：每次 refresh 时要先 verify、再签新对、再写 deny list、再返回，事务性要保证（任一步失败必须回滚以免悬挂状态）。
- 多设备登录时，并发刷新（用户两个 tab 同时 refresh）可能触发"误判重放"，需要短窗口（5s）容忍重复使用同一 refresh_token。

### 中性
- 90d 绝对上限对 99% 用户无感（很少有人连续活跃 90d 不重新登录）。

## 实施清单

- [ ] M0 任务 3：实现 `app/modules/system/services/auth/jwt_service.py`，含 `issue_token_pair()` / `refresh_token_pair()` / `revoke_token_family()`
- [ ] M0 任务 3：Redis key 设计：`jwt:deny:<jti>` (TTL = token exp)、`jwt:chain:<chain_id>:issued_at` (TTL = 90d)
- [ ] M0 任务 3：refresh 接口实现 5 秒并发窗口（同一 jti 在 5s 内重复使用不视为重放，只签新对一次）
- [ ] M0 任务 3：单元测试覆盖：正常刷新、重放检测、并发窗口、90d 绝对上限、整链撤销
- [ ] M0 任务 7：E2E case 覆盖"登录 → 等 access_token 过期 → 自动 refresh → 业务继续"
- [ ] M0 任务 7：E2E case 覆盖"模拟 refresh_token 重放 → 检测到强制重登"

## 替代方案为何被否

- **固定到期 30d**：用户体验差，金融交易场景不可接受。
- **滑动续期不带 Rotation**：失窃 token 永久续命，安全性不足。
- **不加 90d 绝对上限**：极端情况下持续活跃用户的失窃 token 可被攻击者持续 rotation 续命，无收敛机制。
