# ToolFacadeService 缺失方法修复总结

## 问题描述

多个工具在调用 `ToolFacadeService` 时遇到 `AttributeError`，提示缺少以下方法：
- `stock_selection()` - selection_tools.py
- `get_financial_data()` - financial_tools.py  
- `get_kline_chart_url()` - stock_history_tools.py
- `get_chip_distribution()` - stock_history_tools.py
- `get_longhu_data()` - financial_tools.py

## 根本原因

工具层（`app/tools/`）期望 `ToolFacadeService` 提供这些便捷方法，但服务类只实现了底层的 capability 调用方法（如 `run_selector`、`cn_financial_bundle` 等），缺少工具层需要的包装方法。

## 解决方案

在 `ToolFacadeService` 中添加了 5 个工具包装方法：

### 1. `stock_selection()`
```python
def stock_selection(
    self,
    *,
    model_name: str,
    criteria: dict[str, Any] | None = None,
    screening_criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
```
- 合并 `criteria` 和 `screening_criteria` 参数
- 委托给 `run_selector()` capability
- 返回选股结果字典

### 2. `get_financial_data()`
```python
def get_financial_data(
    self,
    ticker: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
```
- 委托给 `cn_financial_bundle()` capability
- 返回财务数据 bundle（可能为空字典）

### 3. `get_kline_chart_url()`
```python
def get_kline_chart_url(self, ticker: str, *, period: str = "1y") -> str:
```
- 生成 K 线图 URL（当前为占位实现）
- 返回格式：`/static/charts/{ticker}_{period}.png`

### 4. `get_chip_distribution()`
```python
def get_chip_distribution(self, ticker: str) -> dict[str, Any]:
```
- 返回筹码分布数据（当前为占位实现）
- 返回空分布和提示信息

### 5. `get_longhu_data()`
```python
def get_longhu_data(self, ticker: str, *, max_rows: int = 15) -> list[dict[str, Any]]:
```
- 返回龙虎榜数据（当前为占位实现）
- 返回空列表

## 测试验证

运行 `tests/application/` 下所有 69 个测试用例，全部通过 ✅

## 实现说明

- `stock_selection()` 和 `get_financial_data()` 是真正的委托方法，调用已有的 capability
- `get_kline_chart_url()`、`get_chip_distribution()`、`get_longhu_data()` 是占位实现，返回合理的默认值
- 所有方法都遵循 `ToolFacadeService` 的设计模式：提供简化的工具层接口，隐藏底层 capability 复杂性

## 后续优化建议

1. **K 线图生成**：实现真实的图表生成逻辑（使用 matplotlib/plotly）
2. **筹码分布**：接入真实的筹码数据源
3. **龙虎榜数据**：从数据库或 API 获取真实龙虎榜数据

这些占位实现确保工具层不会崩溃，同时为未来功能扩展预留了接口。
