from __future__ import annotations

"""将 pytdx 返回值转为 JSON 友好结构。"""


import base64
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)
def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return {"__type__": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    try:
        import pandas as pd

        if isinstance(value, pd.DataFrame):
            return value.to_dict(orient="records")
    except ImportError as e:
        logger.warning("serialize.py.to_jsonable: %s", e)
    if hasattr(value, "_asdict"):
        return to_jsonable(value._asdict())
    if hasattr(value, "__dict__"):
        return to_jsonable(vars(value))
    return str(value)
