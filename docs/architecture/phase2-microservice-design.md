# Phase 2 Design Document: Microservice Decomposition
**Status**: Draft | **Target**: Q3 2026 | **Approach**: Strangler Fig Pattern

## 1. Current State (Monolith)

Quant Atlas runs as a single Flask process serving 124 API routes + WebSocket + Celery workers from one codebase.

### Pain Points
| Issue | Impact |
|-------|--------|
| Single process = single point of failure | Downtime = full platform down |
| Sync I/O blocks worker threads | Quote latency > 1s, backtest blocks requests |
| Memory grows unbounded | OOM after 24h runtime |
| Deployment = all-or-nothing | Cannot deploy market data fix without risk of breaking AI |
| Scaling = vertical only | Cannot scale market data independently |

---

## 2. Target Architecture (Strangler Fig)

### Phase 2A: Extract Edge Services (Weeks 1-4)

```
┌─────────────────────────────────────────────────────┐
│                   API Gateway (Kong/APISIX)          │
│              Routes: /api/v1/market/* → Market Svc   │
│              Routes: /api/v1/strategy/* → Strategy   │
│              Routes: /api/v1/ai/* → AI Agent Svc     │
│              Routes: /api/v1/user/* → User Svc       │
│              Routes: /api/v1/execution/* → Exec Svc  │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
    ┌──────────▼──────┐  ┌────────▼──────────┐
    │  Market Service │  │  Strategy Service │
    │  (Go/Rust)      │  │  (Python FastAPI) │
    │  Port: 5101     │  │  Port: 5102       │
    └──────────┬──────┘  └────────┬──────────┘
               │                    │
    ┌──────────▼────────────────────▼──────────┐
    │          MySQL + Redis + QuestDB          │
    └───────────────────────────────────────────┘
```

**Extraction Order:**
1. **Market Data Service** — Highest traffic, lowest coupling
   - Extract: `app/modules/market_data/services/`
   - Tech: Go (Gin/Echo) or FastAPI + Uvicorn
   - Data: QuestDB (ticks) + Redis (cache)
   - Target latency: < 50ms p99

2. **Strategy Service** — CPU-intensive, benefits from isolation
   - Extract: `app/modules/strategy/services/`
   - Tech: Python FastAPI + Celery workers
   - Target: Non-blocking, async factor calc

3. **Execution Service** — Critical path, needs reliability
   - Extract: `app/modules/execution/services/`
   - Tech: Go (deterministic, low latency)
   - Target: Order placement < 10ms

### Phase 2B: Event-Driven Communication (Weeks 5-8)

Replace direct service calls with Kafka/RabbitMQ:

```python
# Before (sync call)
result = market_service.get_quotes(symbols)

# After (async event)
event_bus.publish(QuoteRequestedEvent(symbols=symbols))
# ... response via callback or separate channel
```

**Events to define:**
- `QuoteUpdated` — market data push
- `SignalGenerated` — strategy → execution
- `OrderPlaced` — execution → portfolio
- `RiskBreach` — risk → strategy halt

### Phase 2C: Data Layer Split (Weeks 9-12)

| Service | Primary DB | Cache | Reason |
|---------|-----------|-------|--------|
| Market | QuestDB | Redis | Time-series optimized |
| Strategy | PostgreSQL | Redis | Relational + JSON |
| Execution | PostgreSQL | Redis | ACID critical |
| User | MySQL | Redis | Existing, stable |

---

## 3. Service Contracts

### Market Service (Go)
```go
// GET /api/v1/market/quotes?symbols=600519,000001
Response: {
  "symbol": "600519",
  "price": 1856.00,
  "change_pct": 1.23,
  "volume": 12345678,
  "timestamp": "2026-06-21T10:30:00Z"
}
```

### Strategy Service (Python FastAPI)
```python
# POST /api/v1/strategy/scan
Request: {"universe": [...], "strategies": [...]}
Response: {"signals": [...], "scan_id": "uuid"}
```

---

## 4. Migration Strategy

### Strangler Fig Pattern
1. **Dual-write period**: New service + old monolith both handle requests
2. **Feature flags**: Route % of traffic to new service
3. **Canary**: 1% → 10% → 50% → 100%
4. **Cutover**: Remove old code path after 2 weeks stable

### Rollback Plan
- API Gateway can reroute to monolith instantly
- Each service has its own DB (no shared schema changes)
- Event queue acts as buffer during migration

---

## 5. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Data inconsistency during split | Medium | Event sourcing + idempotent consumers |
| Increased latency (service mesh) | Low | Co-locate services, use gRPC |
| Team unfamiliar with Go | Medium | Start with Python FastAPI, migrate hot path later |
| Kafka operational complexity | Medium | Start with RabbitMQ (simpler), migrate to Kafka at scale |

---

## 6. Success Criteria

| Metric | Current | Target (Phase 2 End) |
|--------|---------|---------------------|
| API availability | ~95% | 99.9% |
| Market data latency | > 1s | < 50ms p99 |
| Backtest blocking | Yes | No (async queue) |
| Memory usage | Unbounded | Bounded per service |
| Deployment frequency | Weekly | Daily per service |
| Blast radius | Full platform | Single service |

---

## 7. Open Questions

1. **Go vs Python**: Market service needs < 50ms latency — is Go required or is FastAPI + uvloop sufficient?
2. **Data migration**: QuestDB vs ClickHouse for time-series? Need benchmark.
3. **Auth boundary**: JWT token validation at gateway vs per-service?
4. **Monitoring**: OpenTelemetry vs existing logging stack?

---

## 8. Next Steps

1. [ ] Benchmark current latency per endpoint (establish baseline)
2. [ ] Build Market Service MVP (quote endpoint only)
3. [ ] Set up API Gateway + service discovery
4. [ ] Define event schema registry (AsyncAPI)
5. [ ] Create migration runbook for each service
