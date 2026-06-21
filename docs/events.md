# 流式事件清单

> 本文档列出所有 Socket.IO 事件与 SSE 帧。每个事件必须有对应的 pydantic/dataclass model（见 app/domain/events/ 和 app/core/event_bus.py）。
> 迁移流式页面时，把该页面消费的事件加到这里。

## 事件格式约定

每个事件一段，按以下结构：

    ## <event-name> (Socket.IO | SSE)
    - payload: <ModelClassName> (app/domain/events/<file>.py)
    - 触发: <什么条件下发出>
    - 频率: <突发/周期/限流策略>
    - 消费方: <哪些前端页面 / Flutter 屏幕会订阅>

---

## signal.generated (EventBus)

- payload: SignalGeneratedEvent (app/domain/events/handlers.py)
- 触发: 信号生成服务产出新信号
- 频率: 每用户每 symbol 最多 1 次/分钟
- 消费方: 自选股页面、策略看板

## position.opened (EventBus)

- payload: PositionOpenedEvent (app/domain/events/handlers.py)
- 触发: 交易执行开仓
- 频率: 突发
- 消费方: 持仓管理页面、Jarvis 通知

## position.closed (EventBus)

- payload: PositionClosedEvent (app/domain/events/handlers.py)
- 触发: 交易执行平仓
- 频率: 突发
- 消费方: 持仓管理页面、归因分析

## market.regime_changed (EventBus)

- payload: MarketRegimeChangedEvent (app/core/event_bus.py)
- 触发: 市场 regime 检测器状态变化
- 频率: 每日数次
- 消费方: 策略合成、风控模块

## cache.invalidated (CacheInvalidation)

- payload: CacheInvalidationEvent (app/domain/events/cache_invalidation.py)
- 触发: 数据更新时通知缓存失效
- 频率: 高频
- 消费方: 前端 SWR 缓存、后端 Redis 缓存
