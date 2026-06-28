from __future__ import annotations

"""Domain services for RD-Agent configuration parsing."""


from typing import Any


def parse_rdagent_loop_params(body: dict[str, Any]) -> dict[str, Any]:
    """Parse request body into RD-Agent loop parameters (domain logic).

    This function extracts data_scope, budget, search_space fields into
    a normalized loop parameters dictionary.
    """
    ds = body.get("data_scope") if isinstance(body.get("data_scope"), dict) else {}
    budget = body.get("budget") if isinstance(body.get("budget"), dict) else {}
    out: dict[str, Any] = {}

    if ds.get("provider_uri"):
        out["provider_uri"] = ds["provider_uri"]
    if ds.get("market"):
        out["market"] = ds["market"]
    if ds.get("benchmark"):
        out["benchmark"] = ds["benchmark"]

    if budget.get("max_loops") is not None:
        out["loop_n"] = int(budget["max_loops"])
    elif body.get("loop_n") is not None:
        out["loop_n"] = int(body["loop_n"])

    if budget.get("evolving_n") is not None:
        out["evolving_n"] = int(budget["evolving_n"])

    if body.get("search_space") is not None:
        out["search_space_hint"] = body.get("search_space")

    for k in ("provider_uri", "market", "benchmark", "template_dest"):
        if k in body and body[k] is not None:
            out[k] = body[k]

    return out
