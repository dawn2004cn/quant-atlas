"""Portfolio trade import, holdings, and performance routes."""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, request
from flask_login import login_required

from app.application.dto.portfolio_dto import TradeRecordDTO
from app.application.errors import ValidationError
from app.core.middleware.request_context import require_authenticated_user_id
from app.presentation.api.common import ok_response
from app.presentation.api.route_deps import PortfolioRouteDeps, require_portfolio_trade_service
from app.presentation.api.v1_context import ApiV1Context


def register_portfolio_trade_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    route_deps: PortfolioRouteDeps,
) -> None:
    _ = ctx

    @blueprint.post("/portfolio/trades/import")
    @login_required
    def import_trade_records():
        """Import trade records from Excel file."""
        user_id = require_authenticated_user_id()

        try:
            trade_service = require_portfolio_trade_service(route_deps)

            if "file" in request.files:
                f = request.files["file"]
                if f.filename.endswith(".xls") or f.filename.endswith(".xlsx"):
                    import pandas as pd

                    df = pd.read_excel(f)
                    trades = []
                    for _, row in df.iterrows():
                        trade_date = row.get("交易日期") or row.get("date") or row.get("日期")
                        if isinstance(trade_date, str):
                            trade_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
                        elif hasattr(trade_date, "date"):
                            trade_date = trade_date.date()
                        else:
                            continue

                        symbol = str(row.get("股票代码") or row.get("symbol") or row.get("代码", "")).strip()
                        direction = str(row.get("方向") or row.get("direction") or row.get("买卖", "")).upper()
                        if "买" in direction:
                            direction = "BUY"
                        elif "卖" in direction:
                            direction = "SELL"
                        else:
                            continue

                        price = float(row.get("价格") or row.get("price") or row.get("成交价", 0))
                        quantity = int(row.get("数量") or row.get("quantity") or row.get("股数", 0))
                        amount = float(row.get("金额") or row.get("amount") or row.get("成交额", price * quantity))
                        fee = float(row.get("手续费") or row.get("fee") or row.get("佣金", 0))

                        if symbol and price > 0 and quantity > 0:
                            trades.append(
                                TradeRecordDTO(
                                    trade_date=trade_date,
                                    symbol=symbol,
                                    direction=direction,
                                    price=price,
                                    quantity=quantity,
                                    amount=amount,
                                    fee=fee,
                                    user_id=user_id,
                                )
                            )

                    count = trade_service.import_trades(user_id, trades)
                    return ok_response(
                        data={"imported": count, "message": f"成功导入 {count} 条交易记录"},
                        legacy_alias_key=None,
                        enable_legacy_alias=False,
                    )
                raise ValidationError("file_type_not_supported", details={"allowed": [".xls", ".xlsx"]})
            raise ValidationError("file_required")
        except ImportError as exc:
            raise ValidationError(
                "pandas_openpyxl_required",
                details={"hint": "pip install pandas openpyxl"},
            ) from exc
        except ValidationError:
            raise
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValidationError("import_failed", details={"reason": str(exc)}) from exc

    @blueprint.get("/portfolio/trades")
    @login_required
    def list_trade_records():
        """List trade records."""
        user_id = require_authenticated_user_id()

        try:
            trade_service = require_portfolio_trade_service(route_deps)

            start_str = request.args.get("start_date")
            end_str = request.args.get("end_date")
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None

            trades = trade_service.list_trades(user_id, start_date, end_date)
            return ok_response(
                data={"trades": [t.model_dump(mode="json") for t in trades], "count": len(trades)},
                legacy_alias_key=None,
                enable_legacy_alias=False,
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError("trade_list_failed", details={"reason": str(exc)}) from exc

    @blueprint.get("/portfolio/holdings")
    @login_required
    def get_portfolio_holdings():
        """Get calculated holdings from trade history."""
        user_id = require_authenticated_user_id()

        try:
            trade_service = require_portfolio_trade_service(route_deps)

            as_of_str = request.args.get("as_of_date")
            as_of_date = datetime.strptime(as_of_str, "%Y-%m-%d").date() if as_of_str else None

            holdings = trade_service.calculate_holdings(user_id, as_of_date)
            total_value = sum(h["value"] for h in holdings)
            total_cost = sum(h["cost"] for h in holdings)
            total_pnl = total_value - total_cost

            for h in holdings:
                h["weight"] = round(h["value"] / total_value * 100, 2) if total_value > 0 else 0

            return ok_response(
                data={
                    "holdings": holdings,
                    "total_value": round(total_value, 2),
                    "total_cost": round(total_cost, 2),
                    "total_pnl": round(total_pnl, 2),
                    "pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost > 0 else 0,
                },
                legacy_alias_key=None,
                enable_legacy_alias=False,
            )
        except (ValueError, TypeError, AttributeError, ZeroDivisionError) as exc:
            raise ValidationError("holdings_calc_failed", details={"reason": str(exc)}) from exc

    @blueprint.get("/portfolio/performance")
    @login_required
    def get_portfolio_performance():
        """Get portfolio performance (daily/weekly)."""
        user_id = require_authenticated_user_id()

        try:
            trade_service = require_portfolio_trade_service(route_deps)

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            start_str = request.args.get("start_date")
            end_str = request.args.get("end_date")
            if start_str:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            if end_str:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()

            perf = trade_service.calculate_performance(user_id, start_date, end_date)

            weekly = []
            if perf:
                current_week = None
                week_data = []
                for p in perf:
                    week = p.date.isocalendar()[1]
                    if week != current_week:
                        if week_data:
                            weekly.append({
                                "week": current_week,
                                "start_value": week_data[0].total_value - week_data[0].daily_pnl,
                                "end_value": week_data[-1].total_value,
                                "return": round(
                                    (week_data[-1].total_value - week_data[0].total_value)
                                    / week_data[0].total_value
                                    * 100,
                                    2,
                                ),
                            })
                        current_week = week
                        week_data = [p]
                    else:
                        week_data.append(p)
                if week_data:
                    weekly.append({
                        "week": current_week,
                        "start_value": week_data[0].total_value - week_data[0].daily_pnl,
                        "end_value": week_data[-1].total_value,
                        "return": round(
                            (week_data[-1].total_value - week_data[0].total_value)
                            / week_data[0].total_value
                            * 100,
                            2,
                        ),
                    })

            return ok_response(
                data={
                    "daily": [p.model_dump(mode="json") for p in perf],
                    "weekly": weekly,
                },
                legacy_alias_key=None,
                enable_legacy_alias=False,
            )
        except (ValueError, TypeError, AttributeError, ZeroDivisionError) as exc:
            raise ValidationError("performance_calc_failed", details={"reason": str(exc)}) from exc
