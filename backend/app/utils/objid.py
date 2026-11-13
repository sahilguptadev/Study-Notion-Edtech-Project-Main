from typing import Any

from beanie import PydanticObjectId
from bson import ObjectId


def js_type(value: Any) -> str:
    return {str: "string", bool: "boolean", int: "number", float: "number", list: "Array", dict: "Object"}.get(
        type(value), type(value).__name__
    )


class CastError(Exception):
    """Raised when a value cannot be cast to the expected type (bad id, non-numeric price, ...)."""


def to_oid(value: Any, model: str = "Document", path: str = "_id") -> PydanticObjectId:
    if isinstance(value, ObjectId):
        return PydanticObjectId(str(value))
    if isinstance(value, str) and ObjectId.is_valid(value):
        return PydanticObjectId(value)
    raise CastError(
        f'Cast to ObjectId failed for value "{value}" (type {js_type(value)}) at path "{path}" for model "{model}"'
    )


async def find_by_id(model, value: Any):
    """Find by id: missing id -> None, malformed id -> CastError."""
    if value is None:
        return None
    return await model.get(to_oid(value, model.__name__))


def cast_number(value: Any, path: str, model: str | None = None) -> float:
    """Cast to a number (`model` adds a "<Model> validation failed:" prefix to the error text)."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            if value.strip() == "":
                raise ValueError
            return float(value)
        except ValueError:
            pass
    prefix = f"{model} validation failed: {path}: " if model else ""
    raise CastError(f'{prefix}Cast to Number failed for value "{value}" (type {js_type(value)}) at path "{path}"')
