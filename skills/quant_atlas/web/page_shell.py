"""Thin HTML shell helpers — pages.py delegates rendering here (Quant Atlas 6.0)."""

from __future__ import annotations

from flask import render_template
from flask_login import current_user

from app.config import AppSettings, get_settings
from app.core.runtime_config import get_runtime


def ux_env_hints(settings: AppSettings) -> list[dict[str, str | None]]:
    """Non-blocking UI hints for env limits."""
    hints: list[dict[str, str | None]] = []
    if not settings.use_mysql:
        hints.append(
            {
                "tone": "info",
                "title": "当前未启用 MySQL 主库",
                "body": "自选同步、团队协作与部分行情能力需 MySQL；仅 SQLite 时会降级。",
                "href": "/integration-hub",
                "label": "打开集成中枢",
            }
        )
    if not (settings.tdx_root_path or "").strip():
        hints.append(
            {
                "tone": "info",
                "title": "通达信本地路径未配置",
                "body": "离线日线、板块、gbbq 等增强不可用。可在环境变量中设置 TDX_ROOT_PATH。",
                "href": "/capabilities",
                "label": "查看能力说明",
            }
        )
    try:
        from app.core.llm_config import get_llm_config
        llm_config = get_llm_config()
        llm_ready = bool(
            (llm_config.api_key and llm_config.api_key != "EMPTY")
            or (llm_config.base_url or "").strip()
        )
    except Exception:
        llm_ready = bool(
            (get_runtime("OPENAI_API_KEY", "") or "").strip()
            or (get_runtime("OPENAI_BASE_URL", "") or "").strip()
            or (get_runtime("OLLAMA_HOST", "") or "").strip()
        )
    if not llm_ready:
        hints.append(
            {
                "tone": "info",
                "title": "未检测到常见大模型配置",
                "body": "AI 诊股、研究会话等可能不可用。请配置 OPENAI_API_KEY / OLLAMA_HOST。",
                "href": "/integration-hub",
                "label": "排查集成",
            }
        )
    return hints


def render_page_shell(template: str, **context):
    """Render a page template with standard shell context (no business logic)."""
    settings = get_settings()
    payload = {
        "ux_env_hints": ux_env_hints(settings),
    }
    if current_user.is_authenticated:
        payload["username"] = current_user.username
    payload.update(context)
    return render_template(template, **payload)
