# 03 · 快速开始

## 环境要求

- Python **≥ 3.11**（见 `pyproject.toml` → `requires-python`）
- 建议：虚拟环境、Git、Node.js 18+（仅构建 SPA 时需要）
- 可选：Redis、MySQL、Celery Worker

## 安装

```bash
git clone <repository-url>
cd quant-atlas
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 或可编辑安装（含测试扩展）
pip install -e ".[test]"
```

复制环境变量模板并按本地修改（**不要提交真实密钥**）：

```bash
cp .env.example .env
```

关键类别见 [部署](./06-deployment.md)。开发可用 SQLite；生产常用 MySQL + Redis。

## 启动后端

```bash
# 方式一
python run.py

# 方式二
export FLASK_APP=run.py
flask run --host 0.0.0.0 --port 5000
```

健康检查：

```bash
curl -s http://127.0.0.1:5000/api/v1/health
curl -s http://127.0.0.1:5000/api/v1/system/health
```

- `/api/v1/health`：进程存活  
- `/api/v1/system/health`：含 `deployment_status`（ok / degraded / critical）与能力摘要  

二者均为**公开 GET**（无需登录）。

## 启动 SPA（可选）

```bash
cd frontend
npm install
npm run dev
```

默认开发服务器：`http://127.0.0.1:5173`，`base` 为 `/app/`，API 代理到 `5000`。  
生产构建产物由 Flask 挂载到 `/app`（以部署配置为准）。

## 常用验证命令

```bash
pytest -q
ruff check app/
# 可选：路由契约
python scripts/audit_api_routes.py
```

## 下一步

- [架构](./02-architecture.md)
- [API](./04-api.md)
- [贡献](./07-contributing.md)
