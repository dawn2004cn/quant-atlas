from __future__ import annotations



"""Celery task wiring: shared infrastructure bindings and service factories."""







from pathlib import Path



from typing import Any







from app.modules.data.services.basic_market_data_service import BasicMarketDataService



from app.modules.system.services.helpers.market_data_ingestor_access import create_longhu_ingestor



from app.modules.market_data.services.stock_service import StockApplicationService



from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure



from app.config import BASE_DIR, get_settings



from app.domain.ports.market_ports import MarketDataProvider, NewsProvider







_worker_session_factory: Any | None = None











def _create_basic_market_data_repository(settings: Any) -> Any:



    from app.infrastructure.repositories.common.deps import create_basic_market_data_repository







    return create_basic_market_data_repository(settings)











def _create_stock_cache() -> Any:



    from app.infrastructure.repositories.common.deps import create_stock_cache







    return create_stock_cache()











def _create_tdx_gpcw_repository(settings: Any) -> Any:



    from app.infrastructure.repositories.common.deps import create_tdx_gpcw_repository







    return create_tdx_gpcw_repository(settings)











def get_worker_session_factory() -> Any | None:



    """Lazy scoped session factory for Celery worker threads (optional)."""



    global _worker_session_factory



    if _worker_session_factory is not None:



        return _worker_session_factory







    settings = get_settings()



    if not settings.use_mysql:



        return None







    from app.infrastructure.database.orm import (



        create_db_engine,



        create_session_factory,



        mysql_engine_kwargs,



    )







    engine = create_db_engine(settings.database_uri, **mysql_engine_kwargs())



    _worker_session_factory = create_session_factory(engine)



    return _worker_session_factory











def cleanup_worker_scoped_session() -> None:



    """Drop thread-local scoped SQLAlchemy session after a Celery task."""



    global _worker_session_factory



    if _worker_session_factory is None:



        return



    try:



        _worker_session_factory.remove()



    except Exception:



        logger.warning("Suppressed exception", exc_info=True)
        pass











def ensure_task_bindings() -> None:



    """Ensure application helpers are bound in worker processes."""



    bind_application_infrastructure()











def get_market_data_provider() -> MarketDataProvider:



    """Bound market data provider for Celery tasks."""



    ensure_task_bindings()



    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider as _get







    return _get()











def get_news_provider() -> NewsProvider:



    """Bound news provider for Celery tasks."""



    ensure_task_bindings()



    from app.modules.system.services.helpers.news_provider_access import get_news_provider as _get







    return _get()











def create_ta_indicator_provider() -> Any:



    """TA indicator provider factory (infrastructure wired via bootstrap)."""



    from app.bootstrap_components.providers import create_ta_indicator_provider as _create







    return _create()











def create_stock_application_service() -> StockApplicationService:



    """Stock service with market, indicator, and news providers bound."""



    return StockApplicationService(



        get_market_data_provider(),



        create_ta_indicator_provider(),



        get_news_provider(),



    )











def create_cn_tdx_gpcw_provider(*, tdx_root_path: str | Path) -> Any:



    """TDX GPCW file provider for backfill tasks."""



    from app.bootstrap_components.providers import create_cn_tdx_gpcw_provider as _create







    return _create(tdx_root_path=str(tdx_root_path))











def fetch_hk_daily(symbol: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:



    from app.infrastructure.providers.market_history_fetcher import fetch_hk_daily as _fetch







    return _fetch(symbol, start, end)











def fetch_us_daily(symbol: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:



    from app.infrastructure.providers.market_history_fetcher import fetch_us_daily as _fetch







    return _fetch(symbol, start, end)











def fetch_crypto_daily(symbol: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:



    from app.infrastructure.providers.market_history_fetcher import fetch_crypto_daily as _fetch







    return _fetch(symbol, start, end)











def to_db_code(symbol: str, market: str) -> str:



    from app.infrastructure.providers.market_history_fetcher import to_db_code as _to_db_code







    return _to_db_code(symbol, market)











def create_basic_market_data_service(*, with_longhu_adapter: bool = False) -> BasicMarketDataService:



    """Factory for ``BasicMarketDataService`` used by market/backfill tasks."""



    ensure_task_bindings()



    settings = get_settings()



    kwargs: dict[str, Any] = {



        "base_dir": BASE_DIR,



        "tdx_root_path": settings.tdx_root_path,



        "repository": _create_basic_market_data_repository(settings),



    }



    if with_longhu_adapter:



        kwargs["longhu_adapter"] = create_longhu_ingestor()



    return BasicMarketDataService(**kwargs)











def get_task_message_store() -> Any:



    """Task message store with bootstrap bindings applied."""



    ensure_task_bindings()



    from app.modules.system.services.helpers.task_message_access import get_task_message_store as _get







    return _get()











def get_stock_cache() -> Any:



    """Local quote/history cache for Celery tasks."""



    return _create_stock_cache()











def create_tdx_gpcw_task_repository() -> Any:



    """TDX GPCW repository for backfill tasks; ensures table exists when supported."""



    repo = _create_tdx_gpcw_repository(get_settings())



    if hasattr(repo, "table_exists") and hasattr(repo, "create_table"):



        if not repo.table_exists():



            repo.create_table()



    return repo











def ensure_tdx_gpcw_audit_table() -> None:



    """Create audit table for TDX GPCW Celery imports when MySQL is enabled."""



    from app.infrastructure.database.mysql_client import mysql_get_connection







    settings = get_settings()



    mysql = settings.mysql if settings.use_mysql else None



    conn = mysql_get_connection(mysql, autocommit=False)



    try:



        with conn.cursor() as cur:



            cur.execute(



                """



                CREATE TABLE IF NOT EXISTS tdx_gpcw_audit (



                    id INT AUTO_INCREMENT PRIMARY KEY,



                    task_type VARCHAR(16) NOT NULL,



                    source_file VARCHAR(32) NOT NULL,



                    report_date INT NULL,



                    stocks_processed INT DEFAULT 0,



                    rows_written INT DEFAULT 0,



                    rows_skipped INT DEFAULT 0,



                    rows_updated INT DEFAULT 0,



                    status VARCHAR(8) NOT NULL,



                    error_msg TEXT NULL,



                    started_at VARCHAR(64) NOT NULL,



                    finished_at VARCHAR(64) NULL,



                    duration_sec DOUBLE NULL,



                    INDEX idx_task_type (task_type),



                    INDEX idx_status (status)



                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci



                """



            )



        conn.commit()



    finally:



        conn.close()











def create_rdagent_job_store(base_dir: Path) -> Any:



    ensure_task_bindings()



    from app.modules.system.services.helpers.rdagent_access import create_rdagent_job_store as _create







    return _create(base_dir)











def create_rdagent_artifact_registry(base_dir: Path) -> Any:



    ensure_task_bindings()



    from app.modules.system.services.helpers.rdagent_access import create_rdagent_artifact_registry as _create







    return _create(base_dir)











def run_rdagent_factor_mining_loop(



    params: dict[str, Any],



    *,



    progress: Any | None = None,



) -> dict[str, Any]:



    from app.infrastructure.rdagent.rdagent_factor_loop import run_factor_mining_loop







    return run_factor_mining_loop(params, progress=progress)











def append_rdagent_factor_tasks_from_bundle(*, base_dir: Path, run_id: str) -> dict[str, Any]:



    from app.infrastructure.rdagent.factor_catalog_export import append_factor_tasks_from_bundle







    return append_factor_tasks_from_bundle(base_dir=base_dir, run_id=run_id)











def execute_rdagent_qlib_gate(run_id: str, *, base_dir: Path) -> Any:



    from app.infrastructure.rdagent.qlib_gate import execute_rdagent_qlib_gate







    return execute_rdagent_qlib_gate(run_id, base_dir=base_dir)











def generate_ollama_text(*, prompt: str) -> dict[str, Any]:



    """Single-shot Ollama text generation for task-side prompts."""



    from app.bootstrap_components.providers import create_ollama_prompt_adapter







    return create_ollama_prompt_adapter().generate(prompt=prompt)











def init_opentelemetry(



    *,



    service_name: str = "quant-atlas-worker",



    jaeger_endpoint: str | None = None,



    console_export: bool = False,



) -> Any:



    from app.infrastructure.tracing import init_opentelemetry as _init







    return _init(



        service_name=service_name,



        jaeger_endpoint=jaeger_endpoint,



        console_export=console_export,



    )











def get_current_trace_id() -> str | None:



    from app.infrastructure.tracing import get_current_trace_id as _get







    return _get()











def create_swarm_agent_service() -> Any:



    """Swarm agent service for Celery tasks (no app.core.container)."""



    ensure_task_bindings()



    from app.modules.ai_agent.services.swarm_agent_service import SwarmAgentService



    from app.modules.system.services.helpers.agent_access import (



        create_expert_skill_port,



        create_swarm_orchestrator_port,



    )







    return SwarmAgentService(



        swarm_port=create_swarm_orchestrator_port(),



        skill_port=create_expert_skill_port(),



    )











def get_task_progress_store() -> Any:



    from app.infrastructure.messaging.task_progress_store import TaskProgressStore








    return TaskProgressStore()











def init_task_progress(task_id: str, *, task_name: str = "", steps: list[str] | None = None) -> None:



    get_task_progress_store().init(task_id, task_name=task_name, steps=steps)











def report_task_progress(



    task_id: str,



    *,



    step_index: int | None = None,



    message: str = "",



    percent: int | None = None,



) -> None:



    get_task_progress_store().update(



        task_id,



        step_index=step_index,



        message=message,



        percent=percent,



    )











def finalize_task_progress(task_id: str, *, successful: bool, message: str = "") -> None:



    store = get_task_progress_store()



    current = store.get(task_id) or {}



    steps = current.get("steps") or ["æé", "æ§è¡", "å®æ"]



    store.update(



        task_id,



        step_index=len(steps) - 1,



        percent=100 if successful else int(current.get("percent") or 0),



        message=message or ("ä»»å¡å·²å®æ?" if successful else "ä»»å¡å¤±è´¥"),



    )



