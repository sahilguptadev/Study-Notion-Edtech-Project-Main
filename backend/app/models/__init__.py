from app.models.category import Category
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.otp import OTP
from app.models.profile import Profile
from app.models.rating_review import RatingAndReview
from app.models.section import Section, SubSection
from app.models.user import User

ALL_MODELS = [
    User,
    Profile,
    Category,
    Course,
    Section,
    SubSection,
    CourseProgress,
    RatingAndReview,
    OTP,
]

__all__ = [m.__name__ for m in ALL_MODELS] + ["ALL_MODELS"]
