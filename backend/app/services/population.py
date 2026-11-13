"""Helpers that resolve stored ids into full documents. All return plain JSON-ready dicts."""
from beanie import PydanticObjectId

from app.models import Category, Course, Profile, RatingAndReview, Section, SubSection, User
from app.utils.serialize import doc_to_dict


async def fetch_ordered(model, ids: list[PydanticObjectId]) -> list:
    """Docs for `ids`, in order; ids with no matching document are dropped."""
    if not ids:
        return []
    docs = await model.find({"_id": {"$in": list(ids)}}).to_list()
    by_id = {d.id: d for d in docs}
    return [by_id[i] for i in ids if i in by_id]


async def user_with_profile(user: User | None) -> dict | None:
    if user is None:
        return None
    data = doc_to_dict(user)
    profile = await Profile.get(user.additionalDetails)
    data["additionalDetails"] = doc_to_dict(profile) if profile else None
    return data


async def sections_tree(section_ids: list[PydanticObjectId], hide_video: bool = False) -> list[dict]:
    sections = await fetch_ordered(Section, section_ids)
    all_sub_ids = [sid for s in sections for sid in s.subSection]
    subs = {s.id: s for s in await fetch_ordered(SubSection, all_sub_ids)}
    exclude = ("videoUrl",) if hide_video else ()
    out = []
    for section in sections:
        data = doc_to_dict(section)
        data["subSection"] = [doc_to_dict(subs[i], exclude) for i in section.subSection if i in subs]
        out.append(data)
    return out


async def section_with_subs(section: Section | None) -> dict | None:
    if section is None:
        return None
    data = doc_to_dict(section)
    subs = await fetch_ordered(SubSection, section.subSection)
    data["subSection"] = [doc_to_dict(s) for s in subs]
    return data


async def course_with_content(course: Course | None) -> dict | None:
    """populate courseContent -> subSection."""
    if course is None:
        return None
    data = doc_to_dict(course)
    data["courseContent"] = await sections_tree(course.courseContent)
    return data


async def course_full(course: Course | None, hide_video: bool = False) -> dict | None:
    """instructor(+additionalDetails), category, ratingAndReviews, courseContent(+subSection)."""
    if course is None:
        return None
    data = doc_to_dict(course)
    instructor = await User.get(course.instructor)
    data["instructor"] = await user_with_profile(instructor)
    if course.category is not None:
        category = await Category.get(course.category)
        data["category"] = doc_to_dict(category) if category else None
    reviews = await fetch_ordered(RatingAndReview, course.ratingAndReviews)
    data["ratingAndReviews"] = [doc_to_dict(r) for r in reviews]
    data["courseContent"] = await sections_tree(course.courseContent, hide_video)
    return data
