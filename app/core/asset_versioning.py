"""Static asset versioning for cache busting."""

import hashlib
from pathlib import Path

from flask import Flask, current_app, url_for

from app.config import BASE_DIR

import logging
logger = logging.getLogger(__name__)
_STATIC_ROOT = BASE_DIR / "static"


def _resolve_static_root() -> Path:
    try:
        folder = current_app.static_folder
        if folder:
            return Path(folder)
    except RuntimeError as e:
        logger.warning("asset_versioning.py._resolve_static_root: %s", e)
    return _STATIC_ROOT


def get_asset_version(file_path: str) -> str:
    """生成文件的内容哈希作为版本号。"""
    full_path = _resolve_static_root() / file_path
    if not full_path.exists():
        return "0"
    with open(full_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def versioned_url(endpoint: str, **values) -> str:
    """生成带版本参数的 URL。"""
    url = url_for(endpoint, **values)
    # 排除外部 endpoint
    if ":" in endpoint:
        return url
    filename = values.get("filename", "")
    if filename:
        rel_path = filename if endpoint == "static" else f"{endpoint.replace('.', '/')}/{filename}"
        version = get_asset_version(rel_path)
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}v={version}"
    return url


def init_app(app: Flask) -> None:
    """注册模板全局函数。"""
    app.jinja_env.globals["versioned_url"] = versioned_url
