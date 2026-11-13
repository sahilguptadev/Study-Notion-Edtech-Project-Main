from typing import ClassVar, Optional

from beanie import Document

from app.models.base import SerializeMixin


class Profile(SerializeMixin, Document):
    gender: Optional[str] = None
    dateOfBirth: Optional[str] = None
    about: Optional[str] = None
    contactNumber: Optional[float] = None

    KEEP_NULLS: ClassVar[bool] = True

    class Settings:
        name = "profiles"
