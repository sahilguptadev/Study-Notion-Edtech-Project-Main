"""Turn Beanie documents into the JSON shape the frontend expects (`_id`, ISO dates, no secrets)."""
import math
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        # JS Date.toISOString(): millisecond precision + "Z"
        return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None  # JSON.stringify(NaN) -> null
        return int(value) if value.is_integer() else value  # JS has one number type
    return value


def doc_to_dict(doc, exclude: tuple[str, ...] = ()) -> dict:
    """Beanie document -> JSON-ready dict (`_id`, hidden fields removed)."""
    cls = type(doc)
    data = doc.model_dump(by_alias=True, exclude_none=not cls.KEEP_NULLS)
    for key in (*cls.HIDDEN, *exclude):
        data.pop(key, None)
    return jsonable(data)
