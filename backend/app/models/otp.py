from datetime import datetime

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.models.base import SerializeMixin, utcnow


class OTP(SerializeMixin, Document):
    email: str
    otp: str
    createdAt: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "otps"
        # TTL index: MongoDB deletes each OTP 5 minutes after creation.
        indexes = [IndexModel([("createdAt", ASCENDING)], expireAfterSeconds=300)]
