from __future__ import annotations

from flask import Blueprint, request

from ..auth_guard import api_auth_required
from ..responses import success_response


def create_user_blueprint(ctx):
    bp = Blueprint("v2_user", __name__)

    # --- Watchlist ---
    @bp.get("/watchlist")
    @api_auth_required
    def list_watchlists():
        user_id = request.args.get("user_id")
        if user_id:
            result = ctx.watchlist_service.get_user_watchlists(int(user_id))
        else:
            result = ctx.watchlist_service.get_user_watchlists(0)
        return success_response(data=result)

    @bp.post("/watchlist")
    @api_auth_required
    def create_watchlist():
        from ....application.dto import WatchlistCreateDTO
        from .request_parsers import parse_dto
        body = request.get_json(silent=True) or {}
        if ctx.enable_dto_validation:
            dto = parse_dto(body, WatchlistCreateDTO)
            result = ctx.watchlist_service.create_watchlist(
                name=dto.name,
                description=getattr(dto, 'description', ''),
                user_id=dto.user_id if hasattr(dto, 'user_id') else 0,
            )
        else:
            result = ctx.watchlist_service.create_watchlist(
                name=body.get("name", ""),
                description=body.get("description", ""),
                user_id=body.get("user_id", 0),
            )
        return success_response(data=result)

    @bp.get("/watchlist/<int:wl_id>")
    @api_auth_required
    def get_watchlist(wl_id: int):
        result = ctx.watchlist_service.get_watchlist(wl_id)
        return success_response(data=result, meta={"watchlist_id": wl_id})

    @bp.post("/watchlist/<int:wl_id>/stocks")
    @api_auth_required
    def add_watchlist_stock(wl_id: int):
        from ....application.dto import WatchlistAddStockDTO
        from .request_parsers import parse_dto
        body = request.get_json(silent=True) or {}
        if ctx.enable_dto_validation:
            dto = parse_dto(body, WatchlistAddStockDTO)
            result = ctx.watchlist_service.add_stock(wl_id, dto.symbol, dto.market)
        else:
            result = ctx.watchlist_service.add_stock(wl_id, body.get("symbol", ""), body.get("market", "CN"))
        return success_response(data=result)

    @bp.delete("/watchlist/<int:wl_id>/stocks/<symbol>")
    @api_auth_required
    def remove_watchlist_stock(wl_id: int, symbol: str):
        result = ctx.watchlist_service.remove_stock(wl_id, symbol)
        return success_response(data=result, meta={"symbol": symbol})

    # --- Portfolio ---
    @bp.get("/portfolio")
    @api_auth_required
    def list_portfolios():
        user_id = request.args.get("user_id", 0)
        try:
            uid = int(user_id)
        except (ValueError, TypeError):
            uid = 0
        # Using stock_group_service as it's the provider for portfolios in the existing code
        result = ctx.stock_group_service.get_user_portfolios(uid) if ctx.stock_group_service else []
        return success_response(data=result)

    @bp.post("/portfolio")
    @api_auth_required
    def create_portfolio():
        from ....application.dto.v2_dtos import PortfolioCreateDTO
        from .request_parsers import parse_dto
        body = request.get_json(silent=True) or {}
        if ctx.enable_dto_validation and ctx.portfolio_service:
            dto = parse_dto(body, PortfolioCreateDTO)
            result = ctx.portfolio_service.create_portfolio(
                name=dto.name,
                description=getattr(dto, 'description', ''),
                user_id=dto.user_id if hasattr(dto, 'user_id') else 0,
            )
        else:
            result = {"error": "portfolio_service not configured"}
        return success_response(data=result)

    @bp.get("/portfolio/<int:pf_id>")
    @api_auth_required
    def get_portfolio(pf_id: int):
        from ....application.dto.v2_dtos import PortfolioDetailDTO
        from .request_parsers import parse_dto
        if ctx.portfolio_service:
            parse_dto(request.args.to_dict(), PortfolioDetailDTO, partial=True)
            result = ctx.portfolio_service.get_snapshot(pf_id)
        else:
            result = {"error": "portfolio_service not configured"}
        return success_response(data=result)

    @bp.post("/portfolio/<int:pf_id>/rebalance")
    @api_auth_required
    def rebalance_portfolio(pf_id: int):
        from ....application.dto.v2_dtos import PortfolioRebalanceDTO
        from .request_parsers import parse_dto
        body = request.get_json(silent=True) or {}
        if ctx.portfolio_service:
            if ctx.enable_dto_validation:
                dto = parse_dto(body, PortfolioRebalanceDTO)
                result = ctx.portfolio_service.rebalance(pf_id, dto.target_weights)
            else:
                result = ctx.portfolio_service.rebalance(pf_id, body.get("weights", {}))
        else:
            result = {"error": "portfolio_service not configured"}
        return success_response(data=result)

    # --- Groups ---
    @bp.get("/groups")
    @api_auth_required
    def list_groups():
        user_id = request.args.get("user_id", 0)
        try:
            uid = int(user_id)
        except (ValueError, TypeError):
            uid = 0
        if ctx.stock_group_service:
            result = ctx.stock_group_service.get_user_groups(uid)
        else:
            result = []
        return success_response(data=result)

    return bp
