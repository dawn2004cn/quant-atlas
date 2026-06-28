# Quant Atlas

Quantitative research and trading platform — modular monolith with 910+ API routes,
14 context modules, and 190+ registered services.

## Quick Start

```bash
pip install -e ".[test]"
flask run
```

Requires **Python ≥ 3.11**. Set environment variables in `.env` (see `docs/05_Deployment/Deployment_Guide.md`).

## Documentation

| Area | Location |
|------|----------|
| Strategy & Requirements | [`docs/01_Requirements/`](docs/01_Requirements/) |
| Architecture & Design | [`docs/02_Architecture/`](docs/02_Architecture/) |
| Functional Manual | [`docs/03_Functional/`](docs/03_Functional/) |
| Testing Strategy | [`docs/04_Testing/`](docs/04_Testing/) |
| Deployment Guide | [`docs/05_Deployment/`](docs/05_Deployment/) |
| Audit Reports | [`docs/audit/`](docs/audit/) |
| Full index | [`docs/README.md`](docs/README.md) |

## Key Metrics

- **Routes:** 910
- **Python files:** 2,073
- **HTML templates:** 110
- **Lines of code:** ~258K

## Tech Stack

**Backend:** Flask, SQLAlchemy, Celery, LangGraph, Redis  
**Frontend:** jQuery, Bootstrap 4, ECharts, HTMX 2.0  
**Data:** MySQL, QuestDB, Pandas, AkShare, Qlib