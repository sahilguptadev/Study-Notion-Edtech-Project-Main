from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.base import SerializeMixin


class Category(SerializeMixin, Document):
    name: str
    description: Optional[str] = None
    courses: list[PydanticObjectId] = Field(default_factory=list)

    class Settings:
        name = "categories"
        keep_nulls = False
