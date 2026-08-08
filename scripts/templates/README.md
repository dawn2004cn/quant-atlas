# scripts/templates — 历史脚手架副本（不同步）

> **STALE / OUT OF SYNC**（标注于 2026-08-03 · 续二十四）

本目录用于早期脚本/脚手架生成，**不是** Flask 运行时模板路径。

- 生产模板：`app/presentation/web/templates/`
- 生产静态：`static/`
- SPA：`frontend/src/`

已知仍含旧全量行情调用的文件（勿当现行契约）：

- `index.html` — `/api/v1/markets/CN/quotes`
- `market_panorama.html` — `/api/v1/markets/CN/quotes`

生产侧已优先 `quotes/page`。请勿用本目录反向覆盖生产模板。
