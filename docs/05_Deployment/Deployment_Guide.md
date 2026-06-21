# 05 部署文档 (Deployment Guide)

## 1. 快速启动 (Quick Start)
### 环境要求
*   Python 3.10+
*   SQLite 3 (默认数据存储)
*   Flask / Gunicorn

### 启动步骤
1.  **安装依赖**: `pip install -r requirements.txt`
2.  **配置环境**: 修改 `.env` 中的数据库路径与 API 密钥。
3.  **运行启动**: `python run.py` 或 `flask run`
4.  **验证**: 访问 `http://localhost:5000/api/v1/health` 确认所有 14 个模块加载成功。

## 2. 基础设施设置 (Infrastructure)
### 数据湖迁移
系统内置 `LegacyDataMigrationService`，用于将分散的 `.db` 文件合并到统一数据湖：
`POST /api/v1/data-lake/migrate` $\rightarrow$ 扫描根目录 $\rightarrow$ 提取时序表 $\rightarrow$ 写入 `sqlite_lake.db`。

### 内存总线
`GlobalStateBus` 在内存中维护实时状态，部署时需确保单进程模式或使用 Redis 替代方案以支持多进程同步。

## 3. 生产部署方案 (Production)
### 容器化部署 (Proposed)
*   **Image**: 基于 `python:3.10-slim` 构建。
*   **Orchestration**: 使用 Kubernetes (K8s) 部署，将 `DataLake` 挂载为持久化卷 (PVC)。
*   **Scaling**: 
    *   API 节点 $\rightarrow$ 水平扩展 (HPA)。
    *   认知计算节点 $\rightarrow$ 绑定 GPU 资源，独立于 API 节点运行。

### 监控与报警
*   **Health Check**: 通过 `/system/health` 监控各模块状态。
*   **Logging**: 所有 `ServiceError` 和 `ApplicationError` 必须同步至 ELK 或 Sentry。
