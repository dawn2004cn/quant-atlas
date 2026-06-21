# 策略系统二次优化记录 (strategy_plan1.md)

> 本文档记录 strategy_plan1.md 中提出的 6 个维度的策略二次优化

## 目录

1. [组合构建理论升维](#1-组合构建理论升维)
2. [实时风险中间件](#2-实时风险中间件)
3. [信号去重与交叉验证](#3-信号去重与交叉验证)
4. [事件驱动型策略流水线](#4-事件驱动型策略流水线)
5. [高性能计算加速](#5-高性能计算加速)
6. [生产环境数字孪生](#6-生产环境数字孪生)

---

## 1. 组合构建理论升维

**目标**: MVO / Black-Litterman / Risk Budgeting

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 均值方差优化 | `domain/allocation/portfolio_optimizer.py` | `MeanVarianceOptimizer` 基于收益/风险优化 |
| Black-Litterman | `domain/allocation/portfolio_optimizer.py` | `BlackLittermanModel` 贝叶斯观点融合 |
| 风险预算分配 | `domain/allocation/portfolio_optimizer.py` | `RiskBudgetAllocator` 波动率贡献均分 |

### 核心改进

- 相关性矩阵计算，自动检测高相关策略对
- 策略权重相关性 > 0.9 时自动缩减
- 融合投资者观点到先验分布

```python
optimizer = get_portfolio_optimizer()
weights = optimizer.optimize_with_correlation(
    returns={"600519": [...], "000001": [...]},
    expected_returns={"600519": 0.15, "000001": 0.10},
    method="black_litterman",
    correlation_threshold=0.9,
)
```

---

## 2. 实时风险中间件

**目标**: 微秒级执行拦截器

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 头寸限制 | `domain/risk/risk_interceptor.py` | `PositionLimitChecker` 单标的头寸上限 |
| 杠杆检查 | `domain/risk/risk_interceptor.py` | `LeverageChecker` 总账户杠杆检查 |
| 换手率限制 | `domain/risk/risk_interceptor.py` | `TurnoverChecker` 日内换手上限 |
| 流动性校验 | `domain/risk/risk_interceptor.py` | `LiquidityChecker` 成交量/价格偏离检查 |
| 执行拦截器 | `domain/risk/risk_interceptor.py` | `ExecutionInterceptor` 串联所有校验 |

### 核心改进

- 下单前微秒级风险校验链
- 单一标的集中度 ≤ 20%
- 总杠杆 ≤ 1.5x
- 日换手率 ≤ 200%

```python
interceptor = get_execution_interceptor()
result = interceptor.validate_order(order, portfolio_state)
# Result: approved=True, risk_level="low"
```

---

## 3. 信号去重与交叉验证

**目标**: 信号聚类 + 同源因子压减

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 信号聚类 | `domain/allocation/signal_coordinator.py` | `SignalClustering` 按标的聚类相似信号 |
| 因子源归一 | `domain/allocation/signal_coordinator.py` | `FactorSourceNormalizer` 识别同源因子 |
| 信号协调器 | `domain/allocation/signal_coordinator.py` | `SignalCoordinator` 聚合 + 压减同源暴露 |

### 核心改进

- 5 个子策略同时看多，但 3 个同源动量因子 → 自动压减
- 交叉验证：信号一致率 ≥ 60% 才执行
- 因子暴露超过 60% 时自动降低置信度

```python
coordinator = get_signal_coordinator()
aggregated = coordinator.coordinate(signals, factor_exposure_limit=0.6)
# Output: AggregatedSignal with confidence adjustment
```

---

## 4. 事件驱动型策略流水线

**目标**: 非对称事件触发策略调整

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 事件流水线 | `domain/events/event_pipeline.py` | `EventDrivenPipeline` 事件触发器注册 |
| 反应式触发 | `domain/events/event_pipeline.py` | `ReactiveStrategyTrigger` 连接 Agent 证据 |
| 非对称策略 | `domain/events/event_pipeline.py` | `AsymmetricEventStrategies` 预定义处理逻辑 |

### 核心改进

- 财报发布/分红派息/成分股剔除触发策略
- SentimentDepartment 发现负面舆情 → 触发"紧急降仓"
- 事件类型: earnings_warning, sentiment_change, liquidity_shock

```python
pipeline = get_event_pipeline()
pipeline.register_handler("earnings_warning", emergency_reduce)
pipeline.on_evidence("profit_down_50%", {"symbol": "600519"})
# Triggers: MarketEvent(event_type="earnings_warning", severity="high")
```

---

## 5. 高性能计算加速

**目标**: NumPy/Numba 向量化

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 向量化数据 | `domain/compute/vectorized_compute.py` | `VectorizedMarketData` NumPy 数组存储 |
| 加速因子 | `domain/compute/vectorized_compute.py` | `AcceleratedFactors` MA/EMA/RSI/BBands |
| 批处理器 | `domain/compute/vectorized_compute.py` | `BatchProcessor` 5000+ 标的批量扫描 |

### 核心改进

- 因子逻辑下沉到 NumPy 向量化计算
- 批量扫描 5000+ 标的，毫秒级响应
- 支持 MA5/MA20/MA60, EMA12, RSI, Bollinger Bands

```python
engine = get_vectorized_engine()
results = engine.batch_calculate(symbols, market_data, ["ma20", "rsi", "bbands"])
# Returns: {symbol: {"ma20": np.ndarray, "rsi": np.ndarray, ...}}
```

---

## 6. 生产环境数字孪生

**目标**: Shadow Strategy + 自动漂移修正

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 影子策略 | `domain/execution/digital_twin.py` | `ShadowStrategy` 并行运行调参策略 |
| 漂移检测 | `domain/execution/digital_twin.py` | `DriftDetector` 检测实盘/回测偏离 |
| 热切换 | `domain/execution/digital_twin.py` | `AutoHotSwap` 零停机参数切换 |
| 数字孪生 | `domain/execution/digital_twin.py` | `DigitalTwin` 完整系统 |

### 核心改进

- 实盘 A 策略 + 内存并行 B 策略(带微调参数)
- 过去 3 天 B 显著优于 A → 自动触发热切换
- 漂移阈值 5%，超过则建议切换

```python
twin = get_digital_twin()
twin.setup_shadow(live_strategy, adjustment={"stoploss": -0.03})
result = await twin.run_evaluation(market_data)
# If drift > 5%: {"swapped": True, "new_params": {...}}
```

---

## 新增目录结构

```
app/domain/
├── allocation/
│   ├── __init__.py
│   ├── strategy_allocator.py     # [已有]
│   ├── portfolio_optimizer.py     # [新增] MVO/Black-Litterman
│   └── signal_coordinator.py      # [新增] 信号去重
├── risk/
│   ├── __init__.py                # [新增]
│   └── risk_interceptor.py        # [新增] 执行拦截器
├── events/
│   ├── __init__.py                # [新增]
│   └── event_pipeline.py          # [新增] 事件驱动流水线
├── compute/
│   ├── __init__.py                # [新增]
│   └── vectorized_compute.py      # [新增] 向量化计算
├── execution/
│   ├── __init__.py               # [更新] + digital_twin
│   ├── high_fidelity_engine.py   # [已有]
│   └── digital_twin.py           # [新增] 数字孪生
```

---

## 集成关系

| 优化项 | 依赖模块 |
|--------|----------|
| 组合优化 | `FactorLifecycleManager` 因子矩阵 |
| 风险拦截 | `HighFidelityExecutor` 执行前校验 |
| 信号协调 | `EnsembleAllocator` 信号汇总 |
| 事件触发 | `ReactivePipeline` Agent 证据 |
| 向量化计算 | `FactorManager` 因子计算 |
| 数字孪生 | `ConsistencyAuditor` 偏差检测 |

---

## 首选突破点建议

**组合相关性优化 (模块 1)**

理由：
1. 已有 `FactorLifecycleManager` 因子矩阵
2. 相关性计算可瞬间解决"多策略共振"风险
3. 提升大额资金实盘曲线平滑度

---

## 文件清单

```
app/domain/
├── allocation/
│   ├── __init__.py
│   ├── strategy_allocator.py
│   ├── portfolio_optimizer.py      # 新增
│   └── signal_coordinator.py       # 新增
├── risk/
│   ├── __init__.py                  # 新增
│   └── risk_interceptor.py          # 新增
├── events/
│   ├── __init__.py                  # 新增
│   └── event_pipeline.py            # 新增
├── compute/
│   ├── __init__.py                  # 新增
│   └── vectorized_compute.py        # 新增
├── execution/
│   ├── __init__.py                  # 更新
│   ├── high_fidelity_engine.py
│   └── digital_twin.py              # 新增
```

---

## 关键指标

| 优化项 | 优化前 | 优化后 |
|--------|--------|--------|
| 组合构建 | 简单胜率加权 | MVO/Black-Litterman + 相关性检测 |
| 风险控制 | 事后风控 | 微秒级执行前拦截 |
| 信号处理 | 简单汇总 | 同源压减 + 交叉验证 |
| 事件响应 | 周期性轮询 | 事件驱动即时触发 |
| 计算性能 | Pandas 单标 | NumPy 批量 5000+ 标的 |
| 实盘一致性 | 偏差记录 | 影子策略 + 自动热切换 |

---

*文档更新时间: 2026-04-27*
*架构成熟度: 策略系统达到"量化基金生产级"标准*