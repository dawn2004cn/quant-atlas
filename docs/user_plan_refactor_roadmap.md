# user_plan.md 重构路线图

## 目标

把上线后的用户体系从“登录后能使用功能”升级为“个人投资大脑”：权限分层清晰、首页可个性化、自选股成为每日高频入口、关键操作可审计并可用于复盘。

## 第一阶段：用户访问策略与审计基座

- 新增 `UserAccessPolicyService`：按现有角色映射 Guest/Free/Pro/VIP 语义，输出功能限额、市场权限、可用功能和升级提示。
- 新增 `UserAuditTrailService`：记录加入自选、查看推荐、生成诊股、执行回测等关键动作，提供“我的足迹” API。
- 保持现有 Flask-Login/RBAC，不引入 FastAPI/JWT 大迁移；后续认证栈升级单独处理。

## 第二阶段：首页页面管理

- 新增 `PagePreferenceService`：保存首页卡片顺序、隐藏/显示模块、字体大小、移动端优先偏好。
- 今日操盘台前端支持卡片显示/隐藏和顺序读取，先做配置入口，拖拽排序后续增强。

## 第三阶段：自选股深度系统

- 在现有 `WatchlistAgentService` 之上新增更高层的自选股体验契约：排序、预警摘要、批量诊股入口、周/月复盘摘要。
- 加入自选、移除自选、批量操作写入审计；Pro/VIP 后续解除分组和数量限制。

## 第四阶段：个人中心上线化

- 个人中心展示权限权益、用量、升级建议、投资画像、页面偏好、数据导出/删除入口占位。
- 用户可看到自己的访问级别和“还差什么解锁 Pro 能力”。

## 第五阶段：推送与多设备同步

- 接入站内消息、微信/短信推送配置。
- 自选股、画像、页面偏好、报告与审计记录迁移到数据库行级隔离，替代 MVP JSON 存储。

## 第六阶段：合规与商业化

- 支持数据导出、账号删除、隐私同意、订阅升级、团队/机构白名单。
- 高级能力按 Pro/VIP 逐步解锁：多智能体深度报告、Qlib 高级回测、组合压力测试、API 访问。

## 首轮落地范围

本轮实现第一、二、四阶段的基础契约，并把关键入口接入前端：

- `UserAccessPolicyService`
- `UserAuditTrailService`
- `PagePreferenceService`
- API：`/api/v1/user/access-policy`、`/api/v1/user/audit-trail`、`/api/v1/user/page-preferences`
- 前端：个人中心展示权限权益/页面偏好/我的足迹；散户助手显示权限摘要；全站加自选动作写入审计。

## 第二轮落地范围

继续完成第三、五、六阶段的 MVP 契约：

- `WatchlistExperienceService`：自选股智能排序、预警摘要、批量诊股入口、周复盘摘要、分享卡片与导出提示。
- `UserLifecycleService`：推送偏好、多设备同步状态、隐私同意、用户数据导出、账号删除申请、订阅权益摘要。
- API：`/api/v1/watchlist/experience`、`/api/v1/user/lifecycle`、`/api/v1/user/notification-preferences`、`/api/v1/user/privacy-consent`、`/api/v1/user/data-export`、`/api/v1/user/account-deletion-request`。
- 前端：自选股页新增“自选股深度系统”；个人中心新增“推送与同步”“隐私、数据与订阅”；后续可迁移 JSON MVP 存储到数据库 tenant_id 行级隔离。
