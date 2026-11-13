"""Auth dependencies: token check plus Student / Instructor / Admin role guards."""
import jwt
from fastapi import Depends, Request

from app.core.security import decode_token
from app.models import User
from app.utils.http import ApiError, get_body


async def auth(request: Request) -> dict:
    try:
        token = request.cookies.get("token")
        if not token:
            body, _ = await get_body(request)
            token = body.get("token")
        if not token:
            header = request.headers.get("Authorization")
            if header is None:
                raise KeyError("Authorization")  # no Authorization header
            token = header.replace("Bearer ", "")
    except Exception:  # noqa: BLE001
        raise ApiError(401, {"success": False, "message": "Something Went Wrong While Validating the Token"})

    if not token:
        raise ApiError(401, {"success": False, "message": "Token Missing"})
    try:
        return decode_token(token)
    except jwt.PyJWTError:
        raise ApiError(401, {"success": False, "message": "token is invalid"})


def _require(account_type: str, label: str):
    async def guard(user: dict = Depends(auth)) -> dict:
        try:
            db_user = await User.find_one(User.email == user.get("email"))
            wrong_role = db_user.accountType != account_type
        except Exception:  # noqa: BLE001
            raise ApiError(500, {"success": False, "message": "User Role Can't be Verified"})
        if wrong_role:
            raise ApiError(401, {"success": False, "message": f"This is a Protected Route for {label}"})
        return user

    return guard


is_student = _require("Student", "Students")
is_instructor = _require("Instructor", "Instructor")
is_admin = _require("Admin", "Admin")
