# skills/quant_atlas/web — 历史快照（不同步）

> **STALE / OUT OF SYNC**（标注于 2026-08-03 · 续二十三）

本目录下的 HTML/模板是 Quant Atlas **技能包内的历史副本**，用于 skill 演示或离线参考。

它们 **不是** 生产路径：

- 生产经典页：`app/presentation/web/templates/`
- 生产静态脚本：`static/js/`
- 生产 SPA：`frontend/src/`

## 已知漂移（请勿当作现行契约）

以下文件仍可能引用已废弃的全量行情接口（`/api/v1/markets/CN/quotes` 无分页 / 大 `limit`），**请以生产路径为准**：

| 技能副本 | 生产应对 |
|----------|----------|
| `index.html` / `templates/index.html` | 已改 `quotes/page` |
| `market_panorama.html` | 已改 `quotes/page` |
| `hot_sectors.html` | 已改 `quotes/page` |
| `global_radar.html` | 已改 `quotes/page?scope=symbols` |

**不要**假设同步本目录会修复线上行为；若需对齐，应显式从生产模板拷贝并开 PR，而不是反向覆盖生产。
