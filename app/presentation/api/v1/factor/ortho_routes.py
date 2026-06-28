"""Factor orthogonalization and correlation routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_resource
from app.presentation.api.v1.factor._helpers import factors_dataframe
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import require_role, service_fallback


def register_factor_ortho_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.post("/factor/orthogonalize")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_orthogonalization_service")
    def factor_orthogonalize():
        """Orthogonalize a factor against other factors."""
        service = getattr(ctx, "factor_orthogonalization_service", None)
        body = request.get_json(silent=True) or {}

        try:
            df = factors_dataframe(body)
            target_column = body.get("target_column", "").strip()
            if not target_column or target_column not in df.columns:
                raise ValidationError("target_column_not_found", details={"target_column": target_column})

            result = service.orthogonalize(
                factors_df=df,
                target_column=target_column,
                neutralize_columns=body.get("neutralize_columns", []),
                market_column=body.get("market_column"),
            )

            ortho_col = f"{target_column}_ortho"
            return ok_resource(
                resource={
                    "target_column": target_column,
                    "orthogonalized_column": ortho_col,
                    "result": result[[ortho_col]].to_dict(orient="records") if ortho_col in result.columns else [],
                },
                resource_key="factor_ortho",
                enable_legacy_alias=False,
            )
        except ValidationError:
            raise
        except (ValueError, TypeError, KeyError) as exc:
            raise ValidationError("factor_orthogonalize_failed", details={"reason": str(exc)}) from exc

    @blueprint.post("/factor/correlation")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_orthogonalization_service")
    def factor_correlation():
        """Compute factor correlation matrix."""
        service = getattr(ctx, "factor_orthogonalization_service", None)
        body = request.get_json(silent=True) or {}

        try:
            df = factors_dataframe(body, required=False)
            corr = service.compute_factor_correlation_matrix(df)
            return ok_resource(
                resource={"correlation_matrix": corr.to_dict()},
                resource_key="factor_corr",
                enable_legacy_alias=False,
            )
        except ValidationError:
            raise
        except (ValueError, TypeError, KeyError) as exc:
            raise ValidationError("factor_correlation_failed", details={"reason": str(exc)}) from exc
