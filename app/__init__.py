from __future__ import annotations

"""Application factory for the redesigned Flask quant platform.





启动时扩展预热（Qlib / Celery 侧载）由 ``warm_runtime_extensions`` 完成，


并在 ``bootstrap.create_app`` 返回前调用；``from app import create_app`` 与


``from app.bootstrap import create_app`` 均经过同一工厂逻辑。


"""








import logging
from typing import TYPE_CHECKING, Any

from .core.logger import get_logger

logger = logging.getLogger(__name__)


celery_app = None


if TYPE_CHECKING:


    from flask import Flask

    from .config import AppSettings





__all__ = ["create_app", "celery_app", "warm_runtime_extensions"]








def _load_celery_app() -> Any:


    global celery_app


    if celery_app is None:


        try:


            from .celery_app import celery_app as loaded


            celery_app = loaded


        except Exception as exc:


            logger.debug("Celery app lazy load skipped: %s", exc)


            celery_app = None


    return celery_app








def warm_runtime_extensions(app: Flask, settings: AppSettings) -> dict[str, Any]:


    """进程启动时预热：侧载 Celery 任务模块；在 ENABLE_QLIB 时尝试 ``qlib.init``。





    与 TradingAgents-CN 集成：不修改其配置管理器或数据路径；Qlib 仅使用本仓库


    ``provider_uri``（见 ``config/qlib_config.yaml``），可与 TA 侧数据源并行。


    """


    active_celery_app = _load_celery_app()


    meta: dict[str, Any] = {


        "celery_broker_configured": active_celery_app is not None,


        "qlib_warmup": None,


        "openbb_warmup": False,


    }





    if active_celery_app is not None:


        try:


            from .celery_app import discover_task_modules as _discover





            _discover()


        except Exception as e:


            logger.warning("__init__.py.warm_runtime_extensions: %s", e)





    try:


        from openbb_core.app.provider_interface import ProviderInterface


        _ = ProviderInterface()


        meta["openbb_warmup"] = True


    except Exception as exc:


        get_logger(__name__).debug("OpenBB warmup skipped/failed: %s", exc)





    if settings.enable_qlib:


        try:


            from app.modules.data.services.qlib_service import QlibService

            from .config import BASE_DIR





            engine = None


            try:


                from .infrastructure.adapters.quant.qlib_adapter import QlibBacktestAdapter


                engine = QlibBacktestAdapter()


            except Exception as e:


                get_logger(__name__).warning(f"QlibBacktestAdapter not available: {e}")





            if engine:


                meta["qlib_warmup"] = QlibService(engine=engine, base_dir=BASE_DIR).init_qlib()


            else:


                meta["qlib_warmup"] = {"ok": True, "status": "skipped", "message": "Adapter unavailable"}


        except Exception as exc:


            get_logger(__name__).exception("qlib startup warmup failed")


            meta["qlib_warmup"] = {"ok": False, "error": "warmup_exception", "message": str(exc)}





    app.config["RUNTIME_WARMUP"] = meta


    return meta








def create_app():


    from .bootstrap import create_app as _bootstrap_create_app


    return _bootstrap_create_app()


