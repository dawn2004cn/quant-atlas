"""Attribution analyze, report and compare routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.modules.strategy.services.analytics.attribution_compare_service import AttributionCompareService
from app.modules.strategy.services.analytics.unified_attribution_service import UnifiedAttributionService
from app.presentation.api.common import ok_response, parse_market
from app.presentation.api.v1.attribution._helpers import parse_factor_map, parse_positions_payload
from app.presentation.api.v1.attribution.runtime import AttributionRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_attribution_analyze_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None,
    *,
    runtime: AttributionRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/analyze", methods=["GET", "POST"])
    @login_required
    def analyze_performance():
        """Analyze performance drivers (legacy shape + unified DTO fields)."""
        period = request.args.get("period") or (request.get_json(silent=True) or {}).get("period", "30d")
        strategy_name = request.args.get("strategy_name") or (request.get_json(silent=True) or {}).get(
            "strategy_name", "我的策略"
        )
        symbol = (request.args.get("symbol") or (request.get_json(silent=True) or {}).get("symbol") or "").strip() or None
        benchmark_return = float(request.args.get("benchmark_return", 3.5))

        try:
            service = UnifiedAttributionService()
            report = service.build_report(
                strategy_name=strategy_name,
                period=period,
                positions=parse_positions_payload(),
                benchmark_return=benchmark_return,
                symbol=symbol,
                strategy_id=strategy_name,
                factor_exposures=parse_factor_map("exposure"),
                factor_returns=parse_factor_map("factor"),
                alpha=float(request.args.get("alpha", 0.0)),
                include_slippage=request.args.get("include_slippage", "1") != "0",
            )
            payload = report.model_dump(mode="json")
            return ok_response(data=payload, summary=report.summary)
        except (ValidationError, ExternalServiceError):
            raise
        except Exception as exc:
            raise ExternalServiceError(
                "attribution_analyze_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/report", methods=["GET", "POST"])
    @login_required
    def unified_attribution_report():
        """Full unified attribution report (style + factor + slippage)."""
        return analyze_performance()

    @blueprint.route("/compare", methods=["GET"])
    @login_required
    def compare_symbols():
        """Benchmark two symbols on factor attribution shape."""
        base = (request.args.get("symbol") or request.args.get("base") or "").strip().upper()
        peer = (request.args.get("peer") or request.args.get("benchmark_symbol") or "").strip().upper()
        if not base or not peer:
            raise ValidationError("symbol_and_peer_required")
        period = request.args.get("period", "30d")
        market = parse_market(request.args.get("market", "CN"))
        benchmark_return = float(request.args.get("benchmark_return", 3.5))

        try:
            compare_svc = AttributionCompareService(market_service=runtime.market_service)
            dto = compare_svc.compare(
                base_symbol=base,
                peer_symbol=peer,
                market=market,
                period=period,
                benchmark_return=benchmark_return,
            )
            return ok_response(data=dto.model_dump(mode="json"), summary=dto.summary)
        except ValidationError:
            raise
        except Exception as exc:
            raise ExternalServiceError(
                "attribution_compare_failed",
                details={"reason": str(exc)},
            ) from exc
