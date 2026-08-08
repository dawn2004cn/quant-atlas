from __future__ import annotations

"""Tdx 日 K 复权因子与前/后复权计算。"""

from typing import Any

from app.modules.system.services.helpers.tdx_local_access import get_tdx_local_file_port


def calculate_adjustment_factors(
    raw_rows: list[dict[str, Any]], market: str, code: str
) -> list[dict[str, Any]]:
    """基于 xdxr 除权除息数据计算复权因子."""
    if not raw_rows:
        return []

    tdx_port = get_tdx_local_file_port()
    df_xdxr = tdx_port.fetch_xdxr_data(market, code)
    if df_xdxr.empty:
        return [
            {"date": row["date"], "factor": 1.0}
            for row in sorted(raw_rows, key=lambda item: item["date"])
        ]

    return tdx_port.compute_qfq_factors_from_xdxr(raw_rows, df_xdxr)


def apply_forward_adjustment(
    rows: list[dict[str, Any]], factors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return get_tdx_local_file_port().apply_qfq_to_rows(rows, factors)


def apply_backward_adjustment(
    rows: list[dict[str, Any]], factors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    from app.infrastructure.tdx_local.qfq_calculator import apply_hfq_to_rows

    return apply_hfq_to_rows(rows, factors)
