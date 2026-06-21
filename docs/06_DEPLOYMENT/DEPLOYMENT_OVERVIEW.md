# 05 部署指南 (Deployment Guide)

## 1. 快速启动 (Quick Start)
### 启动步骤
1.  **依赖安装**: `pip install -r requirements.txt`
2.  **配置环境**: 设置 `.env` 中的数据库路径与密钥。
3.  **运行**: `python run.py`
4.  **验证**: 访问 `http://localhost:5000/api/v1/health`。

## 2. 基础设施与迁移 (Infrastructure)
### 数据湖迁移
使用 `LegacyDataMigrationService` 将分散的 `.db` 合并：
`POST /api/v1/data-lake/migrate` $\rightarrow$ 扫描 $\rightarrow$ 提取 $\rightarrow$ 写入 `sqlite_lake.db`。

### 状态同步
`GlobalStateBus` 默认内存同步，多进程部署需替换为 Redis 方案。

## 3. 生产环境方案 (Production)
### 容器化部署
*   **Image**: 基于 `python:3.10-slim`。
*   **Orchestration**: K8s 部署，数据湖挂载为 PVC 持久化卷。
*   **Scaling**: API 节点水平扩展 $\rightarrow$ 认知节点绑定 GPU 独立运行。

### 监控与报警
*   **Health Check**: 实时监控 `/system/health`。
*   **Logging**: `ServiceError` 必须同步至 ELK 或 Sentry。
