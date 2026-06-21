# 策略系统优化记录

> 本文档记录 strategy_plan.md 中提出的 5 个维度的策略优化

## 目录

1. [因子全生命周期管理](#1-因子全生命周期管理)
2. [动态多策略组合](#2-动态多策略组合)
3. [环境感知型策略开关](#3-环境感知型策略开关)
4. [高仿真执行引擎](#4-高仿真执行引擎)
5. [策略自愈与自动调优](#5-策略自愈与自动调优)

---

## 1. 因子全生命周期管理

**目标**: 因子 IC/IR 追踪、自动淘汰、正交化

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 因子看板 | `domain/alpha/factor_manager.py` | `FactorDashboard` 实时追踪 IC、IR、换手率 |
| 衰减检测 | `domain/alpha/factor_manager.py` | `FactorDecayDetector` IR 低于阈值时触发告警 |
| 因子中性化 | `domain/alpha/factor_manager.py` | `FactorNeutralizer` 行业/风格中性化 |

### 核心改进

```python
factor_mgr = get_factor_manager()
factor_mgr.track_factor("ma_crossover", ic=0.05, ir=1.2)
decay_alert = factor_mgr.check_decay("ma_crossover")
# Alert: IR below threshold, recommended action: retrain/remove
```

---

## 2. 动态多策略组合

**目标**: Contextual Multi-Armed Bandit + Meta Strategy

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 多臂 bandits | `domain/allocation/strategy_allocator.py` | `ContextualBandit` 根据历史表现动态调权 |
| Meta 策略 | `domain/allocation/strategy_allocator.py` | `MetaStrategy` 资金分配 Agent |
| 集成分配 | `domain/allocation/strategy_allocator.py` | `EnsembleAllocator` 结合 HolyGrail |

### 核心改进

- 基于近期表现自动调低"均线突破"策略权重
- 基于市场状态动态分配资金
- 借鉴 `WeightedAggregator` 的胜率加权逻辑

```python
allocator = get_strategy_allocator()
weights = allocator.compute_ensemble_weights(
    strategies=["ma_cross", "grid", "momentum"],
    context={"regime": "bear", "volatility": "high"}
)
# Output: {"ma_cross": 0.1, "grid": 0.6, "momentum": 0.3}
```

---

## 3. 环境感知型策略开关

**目标**: 情景模版化 + 压力测试自动化

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 策略模板 | `domain/regime/regime_strategy.py` | `RegimeTemplate` 预设牛/熊/震荡参数 |
| 自动切换 | `domain/regime/regime_strategy.py` | `RegimeStrategySwitcher` 根据 regime 调整参数 |
| 压力测试 | `domain/regime/regime_strategy.py` | `StressTestSimulator` 模拟极端场景 |

### 核心改进

- 熊市自动收紧止损 (5% → 2%)
- 增加"空头对冲"因子权重
- 支持"08金融危机"、"20年暴跌"等情景测试

```python
switcher = RegimeStrategySwitcher()
params = switcher.get_adaptive_params("bear", base_params)
# Output: {"stoploss": -0.02, "risk_per_trade": 0.01, "position_size": 0.1}
```

---

## 4. 高仿真执行引擎

**目标**: 滑点模型 + 逐笔撮合 + 一致性审计

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 滑点模型 | `domain/execution/high_fidelity_engine.py` | `SlippageModel` 基于成交量的冲击成本 |
| 逐笔撮合 | `domain/execution/high_fidelity_engine.py` | `TickSimulator` Tick 级订单匹配 |
| 一致性审计 | `domain/execution/high_fidelity_engine.py` | `ConsistencyAuditor` 实盘 vs 回测对比 |

### 核心改进

- 小盘股大额订单冲击成本模拟
- 逐笔撮合避免"未来函数"
- 每日审计偏离度，超阈值自动熔断

```python
executor = get_high_fidelity_executor()
result = executor.execute_with_costs("buy", 100.0, 10000, market_data)
# Output: executed_price=100.15, slippage=0.15, impact_cost=50.0
```

---

## 5. 策略自愈与自动调优

**目标**: Walk-Forward + 贝叶斯优化

### 已实现模块

| 模块 | 文件 | 功能 |
|------|------|------|
| Walk-Forward | `domain/optimization/auto_tuning.py` | `WalkForwardOptimizer` 滚动窗口优化 |
| 贝叶斯优化 | `domain/optimization/auto_tuning.py` | `BayesianOptimizer` 超参搜索 |
| 自愈引擎 | `domain/optimization/auto_tuning.py` | `SelfHealingEngine` 自动参数调整 |

### 核心改进

- 过去 3 个月优化 → 未来 1 个月验证
- Optuna 风格贝叶斯超参搜索
- 自动检测性能衰减并触发重训练

```python
healing = get_self_healing_engine()
result = await healing.auto_tune(StrategyClass, historical_data, param_space)
# Output: {"recommended_params": {...}, "confidence": "high"}
```

---

## 新增目录结构

```
app/domain/
├── alpha/                  # 因子管理
│   ├── __init__.py
│   └── factor_manager.py
├── allocation/             # 资金分配
│   ├── __init__.py
│   └── strategy_allocator.py
├── regime/                 # 市场状态
│   ├── __init__.py
│   └── regime_strategy.py
├── execution/              # 执行引擎
│   ├── __init__.py
│   └── high_fidelity_engine.py
└── optimization/           # 参数优化
    ├── __init__.py
    └── auto_tuning.py
```

---

## 系统集成

### 与 Agent 系统集成

策略优化模块与已有的 Agent 系统无缝集成：

| Agent 模块 | 集成点 |
|------------|--------|
| `MarketRegimeManager` | `RegimeStrategySwitcher` 使用市场状态 |
| `WeightedAggregator` | `ContextualBandit` 借鉴胜率加权逻辑 |
| `AutoValidator` | `StrategyPerformance` 记录策略表现 |

### 优先级建议

**首选突破点**: 动态多策略组合 (模块 2)

理由：
1. 已有 `AutoValidator` 和 `WeightedAggregator` 成功经验
2. 迁移成本低，性价比高
3. 能显著提升实盘收益稳定性

---

## 文件清单

```
app/domain/
├── alpha/
│   ├── __init__.py
│   └── factor_manager.py          # 因子生命周期管理
├── allocation/
│   ├── __init__.py
│   └── strategy_allocator.py      # 动态策略组合
├── regime/
│   ├── __init__.py
│   └── regime_strategy.py         # 环境感知策略开关
├── execution/
│   ├── __init__.py
│   └── high_fidelity_engine.py    # 高仿真执行引擎
└── optimization/
    ├── __init__.py
    └── auto_tuning.py             # 策略自愈与自动调优
```

---

## 关键指标

| 优化项 | 优化前 | 优化后 |
|--------|--------|--------|
| 因子管理 | 无系统追踪 | IC/IR 实时监控 + 自动淘汰 |
| 策略分配 | 静态权重 | Contextual Bandit 动态调权 |
| 策略切换 | 手动调整 | Regime-Based 自动切换 |
| 执行精度 | 简单滑点 | 成交量冲击模型 + 逐笔撮合 |
| 参数优化 | 一次性优化 | Walk-Forward + 贝叶斯搜索 |

---

*文档更新时间: 2026-04-27*
*架构成熟度: 策略系统升级为"自适应+自愈"级别*