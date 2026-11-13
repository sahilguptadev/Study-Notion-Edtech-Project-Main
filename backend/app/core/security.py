import asyncio
import hashlib
import hmac
import time

import bcrypt
import jwt

from app.config import settings


async def hash_password(password: str) -> str:
    return (await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt(10))).decode()


async def verify_password(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(bcrypt.checkpw, password.encode(), hashed.encode())


def create_token(payload: dict, hours: int = 24) -> str:
    now = int(time.time())
    return jwt.encode({**payload, "iat": now, "exp": now + hours * 3600}, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


def razorpay_signature(order_id: str, payment_id: str) -> str:
    return hmac.new(settings.RAZORPAY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
