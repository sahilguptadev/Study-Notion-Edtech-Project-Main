from datetime import datetime
from typing import ClassVar, Literal, Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.base import SerializeMixin, utcnow

ACCOUNT_TYPES = ("Admin", "Student", "Instructor")


class User(SerializeMixin, Document):
    firstName: str
    lastName: str
    email: str
    password: str
    accountType: Literal["Admin", "Student", "Instructor"]
    active: bool = True
    approved: bool = True
    additionalDetails: PydanticObjectId
    courses: list[PydanticObjectId] = Field(default_factory=list)
    token: Optional[str] = None
    resetPasswordExpires: Optional[datetime] = None
    image: Optional[str] = None
    courseProgress: list[PydanticObjectId] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=utcnow)
    updatedAt: datetime = Field(default_factory=utcnow)

    HIDDEN: ClassVar[frozenset] = frozenset({"password"})

    class Settings:
        name = "users"
        keep_nulls = False
