from datetime import datetime
from typing import Literal, Optional

from beanie import Document, PydanticObjectId
from pydantic import Field

from app.models.base import SerializeMixin, utcnow

COURSE_STATUSES = ("Draft", "Published")


class Course(SerializeMixin, Document):
    courseName: Optional[str] = None
    courseDescription: Optional[str] = None
    instructor: PydanticObjectId
    whatYouWillLearn: Optional[str] = None
    courseContent: list[PydanticObjectId] = Field(default_factory=list)
    ratingAndReviews: list[PydanticObjectId] = Field(default_factory=list)
    price: Optional[float] = None
    thumbnail: Optional[str] = None
    tag: list[str]
    category: Optional[PydanticObjectId] = None
    studentsEnroled: list[PydanticObjectId] = Field(default_factory=list)  # (spelling kept: stored field name)
    instructions: list[str] = Field(default_factory=list)
    status: Optional[Literal["Draft", "Published"]] = None
    createdAt: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "courses"
        keep_nulls = False
