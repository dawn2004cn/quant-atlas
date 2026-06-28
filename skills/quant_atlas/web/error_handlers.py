"""Web 页面错误处理器：返回 HTML 模板而非 JSON。"""

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from ..http_static import is_static_asset_request


def register_web_error_handlers(app: Flask) -> None:
    """注册 Web 页面的错误处理器。"""

    @app.errorhandler(404)
    def web_not_found(e):
        if is_static_asset_request() and isinstance(e, HTTPException):
            return e.get_response()
        return render_template("error_404.html"), 404

    @app.errorhandler(500)
    def web_internal_error(e):
        if is_static_asset_request() and isinstance(e, HTTPException):
            return e.get_response()
        return render_template("error_500.html"), 500

    @app.errorhandler(Exception)
    def web_unhandled_error(e):
        if is_static_asset_request() and isinstance(e, HTTPException):
            return e.get_response()
        app.logger.exception("Unhandled error: %s", e)
        return render_template("error_500.html"), 500
