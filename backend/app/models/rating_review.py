from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, IndexModel

from app.models.base import SerializeMixin


class RatingAndReview(SerializeMixin, Document):
    user: PydanticObjectId
    rating: float
    review: str
    course: PydanticObjectId

    class Settings:
        name = "ratingandreviews"
        indexes = [IndexModel([("course", ASCENDING)])]
