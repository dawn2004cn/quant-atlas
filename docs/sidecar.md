# Market FastAPI Sidecar（阶段三 P3-3）

只读行情边缘服务，通过 `httpx` 异步代理 Flask 单体 `/api/v1/markets/{market}/quotes`。

## 本地运行

```bash
# 终端 1：Flask
python run.py

# 终端 2：侧车
pip install -r sidecar/market/requirements.txt
FLASK_UPSTREAM=http://127.0.0.1:5000 uvicorn sidecar.market.main:app --port 8001
```

- `GET http://127.0.0.1:8001/health`
- `GET http://127.0.0.1:8001/price/600519?market=CN`
- OpenAPI：`http://127.0.0.1:8001/docs`

## Docker Compose

```bash
docker compose --profile sidecar up -d market-sidecar
```

侧车监听 `8001`，上游为 compose 网络内的 `web:5000`。

单体异步行情回补（T-5，可选）：

```bash
# .env 或 compose 环境变量（默认 0）
ENABLE_ASYNC_MARKET_QUOTES=1
docker compose up -d web
```

## 设计原则

- **不迁移**现有 575+ Flask 路由
- 新对外 OpenAPI 只读场景走侧车；写操作仍在 Flask
- 压测对比见 `docs/perf_baseline.md`
