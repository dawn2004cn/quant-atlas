"""Serve built React SPA from /app (Phase H)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Response, abort, send_from_directory

from app.config import BASE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

_SPA_DIST = BASE_DIR / "frontend" / "dist"


def register_spa_pages(blueprint: Blueprint) -> None:
    """Mount production build at /app/*; assets under /app/assets/."""

    @blueprint.route("/app")
    @blueprint.route("/app/<path:asset_path>")
    def spa_shell(asset_path: str = "") -> Response:
        if not _SPA_DIST.is_dir():
            abort(
                404,
                description="SPA 未构建。请在 frontend/ 目录运行 npm install && npm run build",
            )

        if asset_path:
            candidate = _SPA_DIST / asset_path
            if candidate.is_file():
                return send_from_directory(_SPA_DIST, asset_path)

        index = _SPA_DIST / "index.html"
        if not index.is_file():
            abort(404, description="frontend/dist/index.html 缺失")
        return send_from_directory(_SPA_DIST, "index.html")

    logger.debug("SPA routes registered at /app (dist=%s)", _SPA_DIST)
