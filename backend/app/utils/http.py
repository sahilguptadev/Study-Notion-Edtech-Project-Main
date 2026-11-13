"""Request/response helpers that keep the API's JSON shapes and status codes consistent."""
import json
import logging
import math
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from app.utils.serialize import jsonable


class ApiError(Exception):
    """Raise to send an exact JSON body with a given HTTP status."""

    def __init__(self, status: int, content: dict):
        self.status = status
        self.content = content


def send(content: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(content=jsonable(content), status_code=status)


def js_falsy(value: Any) -> bool:
    """Truthiness as the JavaScript client defines it: [] and {} are truthy, unlike Python."""
    if value is None or value is False or value == "":
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0 or (isinstance(value, float) and math.isnan(value))
    return False


async def get_body(request: Request) -> tuple[dict, dict[str, UploadFile]]:
    """Parse the request body (JSON or multipart form) into (fields, uploaded files). Cached per request."""
    cached = getattr(request.state, "_parsed_body", None)
    if cached is not None:
        return cached
    body: dict = {}
    files: dict[str, UploadFile] = {}
    ctype = request.headers.get("content-type", "")
    try:
        if "application/json" in ctype:
            data = await request.json()
            body = data if isinstance(data, dict) else {}
        elif "multipart/form-data" in ctype or "application/x-www-form-urlencoded" in ctype:
            form = await request.form()
            for key, val in form.multi_items():
                if isinstance(val, UploadFile):
                    if val.filename:
                        files[key] = val
                else:
                    body[key] = val
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}
    request.state._parsed_body = (body, files)
    return request.state._parsed_body


def log_error() -> None:
    """Call inside `except`: keeps the traceback in the server logs."""
    logging.getLogger("studynotion").exception("unhandled error in route")
