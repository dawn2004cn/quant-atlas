from __future__ import annotations
"""Serve project-root ``static/`` and ``instance/uploads/`` reliably."""


import re
from pathlib import Path

from flask import Flask, abort, send_from_directory

from ..core.logger import get_logger

logger = get_logger(__name__)
_VENDOR_RE = re.compile(r"(vendor/|\.min\.)")


def _safe_upload_path(base: Path, filename: str) -> Path:
    resolved_base = base.resolve()
    candidate = (resolved_base / filename).resolve()
    try:
        candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise abort(403) from exc
    return candidate


def _vendor_max_age(filename: str) -> int:
    """Cache vendor/minified assets for 7 days, others for 1 hour."""
    return 604800 if _VENDOR_RE.search(filename) else 3600


def configure_static_files(app: Flask, static_root: Path) -> None:
    """Pin static serving to an absolute directory under the repo root."""
    root = static_root.resolve()
    app.config["STATIC_ROOT"] = str(root)

    if not app.has_static_folder:
        logger.warning("Flask static route not registered; static_folder is unset")
        return

    def send_static(filename: str):
        return send_from_directory(
            str(root),
            filename,
            max_age=_vendor_max_age(filename),
        )

    app.view_functions["static"] = send_static
    logger.info("Static files: %s", root)

    uploads_dir = Path(app.instance_path) / "uploads"
    if not uploads_dir.exists():
        uploads_dir.mkdir(parents=True, exist_ok=True)

    @app.route("/uploads/<path:filename>")
    def send_upload(filename: str):
        upload_path = _safe_upload_path(uploads_dir, filename)
        return send_from_directory(
            str(upload_path.parent),
            upload_path.name,
        )

    logger.info("Uploads route: /uploads/ -> %s", uploads_dir)
