from __future__ import annotations
from ..celery_app import celery as _celery

if _celery is not None:

    from ..bootstrap import create_app
    from app.core.logger import get_logger
    from app.application.request_executor import run_async

    logger = get_logger(__name__)

    @_celery.task(name="tasks.ten_kings_daily_sniper")
    def run_ten_kings_sniper():
        """每日收盘后执行天王狙击扫描。"""
        try:
            app = create_app()
            with app.app_context():
                svc = app.extensions["api_bundle"].services.ten_kings_sniper_service
                if svc:
                    res = run_async(svc.run_daily_scan())
                    logger.info(f"TenKings Daily Sniper completed: {res}")
                else:
                    logger.error("TenKingsSniperService not initialized")
        except Exception as e:
            logger.exception(f"TenKings Daily Sniper task failed: {e}")

    @_celery.task(name="tasks.ten_kings_position_tracker")
    def track_ten_kings_positions():
        """定时追踪持仓盈亏。"""
        try:
            app = create_app()
            with app.app_context():
                svc = app.extensions["api_bundle"].services.ten_kings_sniper_service
                if svc:
                    svc.track_positions()
                else:
                    logger.error("TenKingsSniperService not initialized")
        except Exception as e:
            logger.exception(f"TenKings Position Tracker task failed: {e}")

else:
    run_ten_kings_sniper = None
    track_ten_kings_positions = None
