# 06 · 部署指南（对外）

本文描述**部署轮廓与配置类别**。不包含真实密钥、内网 IP 或生产口令。

## 运行模式

| 模式 | 说明 |
|------|------|
| 单机开发 | `python run.py` / `flask run`；SQLite 可选 |
| 生产 API | Gunicorn / 容器托管 Flask app；反向代理 TLS |
| 异步任务 | Celery Worker + Broker（Redis 等），按特性开关启用 |
| 前端 | 构建 `frontend` 静态资源，由 Flask 或 CDN 提供 `/app` |

参考容器文件：仓库根 `Dockerfile`、`docker-compose.yml`（以实际服务定义为准）。

## 配置类别（变量名级）

从 `.env.example` 归类（写入 `.env`，勿提交密钥）：

| 类别 | 示例变量 | 用途 |
|------|----------|------|
| Flask | `FLASK_APP`、`FLASK_SECRET_KEY`、`FLASK_DEBUG` | 应用入口与会话 |
| 数据库 | `MYSQL_*`、读写分离相关 | 主库 / 只读 |
| 缓存 | `REDIS_URL` | 缓存、Broker、任务 |
| 安全 | `SKIP_SECRETS_CHECKS`（仅 CI/本地） | 扫描豁免，生产勿滥用 |
| 数据源 | TDX / Tushare 等 | 行情与基本面（按需） |
| 通知 | 邮件 / 钉钉 / 微信相关 | 告警通道 |

生产要求：

- 使用强随机 `FLASK_SECRET_KEY`  
- 数据库与 Redis 使用私网与 ACL  
- 关闭 Debug；限制 CORS / CSRF 按部署策略配置  

## 健康与就绪

```text
GET /api/v1/health           → 存活
GET /api/v1/system/health    → deployment_status + services
```

编排探针建议：

- **liveness**：`/api/v1/health`  
- **readiness**：`/api/v1/system/health` 且 `deployment_status != critical`（按你们 SLO 调整）

## 数据与迁移

- ORM / 结构变更：Alembic（`alembic/`）  
- 遗留 `.db` 合并：数据湖相关 API / 服务（见内部数据湖文档，实验性能力请勿对外承诺 SLA）

## 安全提示

- 绝不把生产密钥写入文档或提交到 Git  
- QMT / IBKR 等实盘路径默认应有预检、权限与 kill-switch 策略  
- 公开 API 白名单刻意保持极小（见 [API](./04-api.md)）

## 更多

内部运维清单（非对外契约）：`docs/05_Deployment/`、`docs/ops/`
