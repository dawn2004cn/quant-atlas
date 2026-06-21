"""Hot sector API sub-package."""

from app.presentation.api.v1.hot_sectors.ingest_routes import register_hot_sector_ingest_routes
from app.presentation.api.v1.hot_sectors.list_routes import register_hot_sector_list_routes
from app.presentation.api.v1.hot_sectors.member_routes import register_hot_sector_member_routes
from app.presentation.api.v1.hot_sectors.runtime import HotSectorRuntime

__all__ = [
    "HotSectorRuntime",
    "register_hot_sector_ingest_routes",
    "register_hot_sector_list_routes",
    "register_hot_sector_member_routes",
]
