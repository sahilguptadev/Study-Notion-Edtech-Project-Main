from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.base import SerializeMixin


class CourseProgress(SerializeMixin, Document):
    courseID: Optional[PydanticObjectId] = None
    userId: Optional[PydanticObjectId] = None
    completedVideos: list[PydanticObjectId] = Field(default_factory=list)

    class Settings:
        name = "courseprogresses"
        keep_nulls = False
