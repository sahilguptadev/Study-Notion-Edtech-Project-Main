import random
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core.deps import auth
from app.core.security import create_token, hash_password, verify_password
from app.models import OTP, Profile, User
from app.models.base import utcnow
from app.models.user import ACCOUNT_TYPES
from app.services.population import user_with_profile
from app.utils.http import get_body, js_falsy, send, log_error
from app.utils.mail import mail_sender, render_template
from app.utils.objid import find_by_id

router = APIRouter()


def _email(value):
    return value.strip() if isinstance(value, str) else value


def _generate_otp() -> str:
    return "".join(random.choice("0123456789") for _ in range(6))


@router.post("/signup")
async def signup(request: Request):
    try:
        body, _ = await get_body(request)
        first_name, last_name = body.get("firstName"), body.get("lastName")
        email, password = body.get("email"), body.get("password")
        confirm_password, account_type = body.get("confirmPassword"), body.get("accountType")
        otp = body.get("otp")

        if any(js_falsy(v) for v in (first_name, last_name, email, password, confirm_password, otp)):
            return send({"success": False, "message": "All Fields are required"}, 403)
        if password != confirm_password:
            return send(
                {"success": False, "message": "Password and Confirm Password do not match. Please try again."}, 400
            )
        email = _email(email)
        if await User.find_one(User.email == email):
            return send({"success": False, "message": "User already exists. Please sign in to continue."}, 400)

        latest = await OTP.find(OTP.email == email).sort("-createdAt").limit(1).to_list()
        if not latest or str(otp) != latest[0].otp:
            return send({"success": False, "message": "The OTP is not valid"}, 400)

        if account_type not in ACCOUNT_TYPES:
            raise ValueError("accountType is required")  # invalid account type -> 500
        hashed = await hash_password(password)

        profile = Profile(gender=None, dateOfBirth=None, about=None, contactNumber=None)
        await profile.insert()
        user = User(
            firstName=first_name.strip(),
            lastName=last_name.strip(),
            email=email,
            password=hashed,
            accountType=account_type,
            approved=True,
            additionalDetails=profile.id,
            image="",
        )
        await user.insert()
        return send({"success": True, "user": _user_dict(user), "message": "User registered successfully"})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "User cannot be registered. Please try again."}, 500)


def _user_dict(user: User) -> dict:
    from app.utils.serialize import doc_to_dict

    return doc_to_dict(user)


@router.post("/login")
async def login(request: Request):
    try:
        body, _ = await get_body(request)
        email, password = body.get("email"), body.get("password")
        if js_falsy(email) or js_falsy(password):
            return send({"success": False, "message": "Please Fill up All the Required Fields"}, 400)

        user = await User.find_one(User.email == _email(email)) if isinstance(email, str) else None
        if not user:
            return send(
                {"success": False, "message": "User is not Registered with Us Please SignUp to Continue"}, 401
            )

        if isinstance(password, str) and await verify_password(password, user.password):
            token = create_token({"email": user.email, "id": str(user.id)})
            data = await user_with_profile(user)
            data["token"] = token
            response = send({"success": True, "token": token, "user": data, "message": "User Login Success"})
            response.set_cookie("token", token, max_age=3 * 24 * 3600, httponly=True)
            return response
        return send({"success": False, "message": "Password is incorrect"}, 401)
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Login Failure Please Try Again"}, 500)


@router.post("/sendotp")
async def sendotp(request: Request):
    try:
        body, _ = await get_body(request)
        email = body.get("email")
        if isinstance(email, str) and await User.find_one(User.email == _email(email)):
            return send({"success": False, "message": "User is Already Registered"}, 401)

        otp = _generate_otp()
        while await OTP.find_one(OTP.otp == otp):
            otp = _generate_otp()
        await OTP(email=email, otp=otp).insert()
        # Send the OTP email (failures are logged, never raised).
        await mail_sender(email, "Verification Email", render_template("emailVerificationTemplate", otp=otp))
        return send({"success": True, "message": "OTP Sent Successfully", "otp": otp})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "error": str(exc)}, 500)


@router.post("/changepassword")
async def change_password(request: Request, current: dict = Depends(auth)):
    try:
        body, _ = await get_body(request)
        user = await find_by_id(User, current.get("id"))
        old_password, new_password = body.get("oldPassword"), body.get("newPassword")
        if not isinstance(old_password, str) or not isinstance(new_password, str):
            raise ValueError("data and hash arguments required")
        if not await verify_password(old_password, user.password):
            return send({"success": False, "message": "The password is incorrect"}, 401)

        user.password = await hash_password(new_password)
        user.updatedAt = utcnow()
        await user.save()
        await mail_sender(
            user.email,
            "Password for your account has been updated",
            render_template(
                "passwordUpdate",
                email=user.email,
                name=f"Password updated successfully for {user.firstName} {user.lastName}",
            ),
        )
        return send({"success": True, "message": "Password updated successfully"})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send(
            {"success": False, "message": "Error occurred while updating password", "error": str(exc)}, 500
        )


@router.post("/reset-password-token")
async def reset_password_token(request: Request):
    try:
        body, _ = await get_body(request)
        email = body.get("email")
        user = await User.find_one(User.email == _email(email)) if isinstance(email, str) else None
        if not user:
            return send(
                {"success": False, "message": f"This Email: {email} is not Registered With Us Enter a Valid Email "}
            )
        token = secrets.token_hex(20)
        user.token = token
        user.resetPasswordExpires = utcnow() + timedelta(hours=1)
        user.updatedAt = utcnow()
        await user.save()

        url = f"{settings.FRONTEND_URL}/update-password/{token}"
        await mail_sender(
            email,
            "Password Reset",
            f"Your Link for email verification is {url}. Please click this url to reset your password.",
        )
        return send(
            {"success": True, "message": "Email Sent Successfully, Please Check Your Email to Continue Further"}
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"error": str(exc), "success": False, "message": "Some Error in Sending the Reset Message"})


@router.post("/reset-password")
async def reset_password(request: Request):
    try:
        body, _ = await get_body(request)
        password, confirm_password, token = body.get("password"), body.get("confirmPassword"), body.get("token")
        if confirm_password != password:
            return send({"success": False, "message": "Password and Confirm Password Does not Match"})
        user = await User.find_one(User.token == token) if isinstance(token, str) and token else None
        if not user:
            return send({"success": False, "message": "Token is Invalid"})
        if not (user.resetPasswordExpires and user.resetPasswordExpires > utcnow()):
            return send({"success": False, "message": "Token is Expired, Please Regenerate Your Token"}, 403)
        user.password = await hash_password(password)
        user.updatedAt = utcnow()
        await user.save()
        return send({"success": True, "message": "Password Reset Successful"})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"error": str(exc), "success": False, "message": "Some Error in Updating the Password"})
