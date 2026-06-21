# Quant Atlas V1–V9 集成验收

> **本文档已合并至** [`option_1_9.md`](./option_1_9.md)（演进纪要 + 验收矩阵 + 自动化命令 + 结论）。

请使用 **option_1_9.md** 作为唯一收口来源：

- **§1** 版本与 Option 对照（含 V8/V9 命名纠正）
- **§2** 分阶段交付与验收矩阵
- **§3** 集成验收（pytest + 人工清单）
- **§4–§5** 缺口与结论

快速命令：

```powershell
python -m pytest tests/integration/test_v1_v9_acceptance_smoke.py -q
```
