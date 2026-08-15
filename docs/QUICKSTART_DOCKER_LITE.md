# Quant Atlas — 轻量自测（Docker Lite）

用于本地快速拉起 **Redis + Web（SQLite）**，不依赖 MySQL / Celery Worker。

## 启动

```bash
docker compose --profile lite up -d --build
```

- Web：http://localhost:5000  
- SPA：http://localhost:5000/app/  
- Redis：localhost:6379  

## 说明

| 项 | 行为 |
|----|------|
| 数据库 | `DATABASE_BACKEND=sqlite`（数据在 `instance/`） |
| Cookie | `SESSION_COOKIE_SECURE=0`，HTTP Session 可登录 |
| Worker / Beat / MySQL | 不启动（完整栈用默认 `docker compose up -d`） |

## 停止

```bash
docker compose --profile lite down
```
