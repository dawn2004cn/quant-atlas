# Quant Atlas

智能零售投研与量化交易平台（模块化单体）：行情与研究、回测与因子、多智能体分析、组合风控与执行适配。

- **API**：900+ 路由量级（以运行注册为准）  
- **模块**：14 个上下文模块  
- **前端**：React SPA（`/app`）+ 经典 Jinja 页  

## 快速开始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

要求 **Python ≥ 3.11**。健康检查：`GET /api/v1/health`。

SPA 开发：

```bash
cd frontend && npm install && npm run dev
```

## 对外技术文档

| 文档 | 说明 |
|------|------|
| **[docs/public/](docs/public/README.md)** | **对外技术文档门户（从这里开始）** |
| [概览](docs/public/01-overview.md) | 产品定位与边界 |
| [架构](docs/public/02-architecture.md) | 分层与模块 |
| [快速开始](docs/public/03-getting-started.md) | 安装启动 |
| [API](docs/public/04-api.md) | 版本、鉴权、公开路径 |
| [SDK](docs/public/05-strategy-sdk.md) | `app.sdk` 与扩展 |
| [部署](docs/public/06-deployment.md) | 部署轮廓 |
| [贡献](docs/public/07-contributing.md) | 贡献指南 |

工程向完整索引（含内部资料）：[`docs/README.md`](docs/README.md)

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Flask、SQLAlchemy、Celery、LangGraph、Redis |
| 前端 | React、Vite、SWR（SPA）；Jinja 经典页仍可用 |
| 数据 | MySQL / SQLite、Pandas、AkShare、Qlib 等 |

## 许可与安全

请勿在 Issue / PR 中粘贴生产密钥或客户数据。实盘相关功能默认应有安全闸门。
