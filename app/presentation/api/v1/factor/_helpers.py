"""Factor route helpers."""

from __future__ import annotations

import json

import pandas as pd

from app.application.errors import ValidationError


def factors_dataframe(body: dict, *, required: bool = True) -> pd.DataFrame:
    factors_json = body.get("factors", "[]")
    if isinstance(factors_json, str):
        factors_data = json.loads(factors_json)
    else:
        factors_data = factors_json
    if required and not factors_data:
        raise ValidationError("factors_required")
    return pd.DataFrame(factors_data)
