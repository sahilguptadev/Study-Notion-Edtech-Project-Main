from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.base import SerializeMixin


class Section(SerializeMixin, Document):
    sectionName: Optional[str] = None
    subSection: list[PydanticObjectId] = Field(default_factory=list)

    class Settings:
        name = "sections"
        keep_nulls = False


class SubSection(SerializeMixin, Document):
    title: Optional[str] = None
    timeDuration: Optional[str] = None
    description: Optional[str] = None
    videoUrl: Optional[str] = None

    class Settings:
        name = "subsections"
        keep_nulls = False
