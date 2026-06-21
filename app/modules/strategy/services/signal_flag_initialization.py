"""Delegate signal-flag service initialization to keep services.py lightweight."""
import logging

logger = logging.getLogger(__name__)


def init_signal_flag_service(services, settings):
    """Initialize SignalFlagScannerService with repository from settings."""
    from app.config import get_settings
    from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
    from app.infrastructure.repositories.deps import create_signal_flag_pool_repository

    s = settings or get_settings()
    repo = create_signal_flag_pool_repository(s)
    services.signal_flag_service = SignalFlagScannerService(
        stock_service=services.stock_service,
        stock_cache=services._stock_cache,
        repository=repo,
        enable_qlib=False,
    )
