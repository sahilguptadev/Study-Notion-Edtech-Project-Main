import json
import random

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core.deps import auth, is_admin, is_instructor, is_student
from app.models import Category, Course, CourseProgress, RatingAndReview, Section, SubSection, User
from app.models.base import utcnow
from app.models.course import COURSE_STATUSES
from app.services.population import (
    course_full,
    course_with_content,
    fetch_ordered,
    section_with_subs,
    sections_tree,
)
from app.utils.duration import convert_seconds_to_duration, parse_int
from app.utils.http import get_body, js_falsy, send, log_error
from app.utils.objid import CastError, cast_number, find_by_id, to_oid
from app.utils.serialize import doc_to_dict
from app.utils.uploader import upload_to_cloudinary

router = APIRouter()


def _col(model):
    return model.get_motor_collection()


def _json_list(value):
    """The client sends tag/instructions as JSON-encoded arrays inside the form data."""
    return json.loads(value) if isinstance(value, (str, bytes)) else value


def _total_seconds(content: list[dict]) -> int:
    return sum(parse_int(s.get("timeDuration")) for sec in content for s in sec["subSection"])


def _agg_oid(value):
    """`new mongoose.Types.ObjectId(x)` error wording."""
    try:
        return to_oid(value)
    except CastError:
        raise CastError(
            "Argument passed in must be a string of 12 bytes or a string of 24 hex characters or an integer"
        ) from None


def _check_status(value):
    if value not in COURSE_STATUSES:
        raise ValueError(
            f"Course validation failed: status: `{value}` is not a valid enum value for path `status`."
        )


# ───────────────────────────── Courses ─────────────────────────────


@router.post("/createCourse")
async def create_course(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, files = await get_body(request)
        user_id = current.get("id")
        thumbnail = files.get("thumbnailImage")
        if not files:  # no file was uploaded
            raise TypeError("Cannot read properties of undefined (reading 'thumbnailImage')")
        tag = _json_list(body.get("tag"))
        instructions = _json_list(body.get("instructions"))
        course_name, description = body.get("courseName"), body.get("courseDescription")
        what_you_will_learn, price = body.get("whatYouWillLearn"), body.get("price")
        category, status = body.get("category"), body.get("status")

        if (
            js_falsy(course_name)
            or js_falsy(description)
            or js_falsy(what_you_will_learn)
            or js_falsy(price)
            or not len(tag)
            or thumbnail is None
            or js_falsy(category)
            or not len(instructions)
        ):
            return send({"success": False, "message": "All Fields are Mandatory"}, 400)
        if js_falsy(status):
            status = "Draft"

        instructor = await find_by_id(User, user_id)
        if not instructor:
            return send({"success": False, "message": "Instructor Details Not Found"}, 404)
        category_doc = await find_by_id(Category, category)
        if not category_doc:
            return send({"success": False, "message": "Category Details Not Found"}, 404)

        price = cast_number(price, "price", "Course")
        _check_status(status)
        image = await upload_to_cloudinary(thumbnail, settings.FOLDER_NAME)
        course = Course(
            courseName=course_name,
            courseDescription=description,
            instructor=instructor.id,
            whatYouWillLearn=what_you_will_learn,
            price=price,
            tag=tag,
            category=category_doc.id,
            thumbnail=image["secure_url"],
            status=status,
            instructions=instructions,
        )
        await course.insert()
        await _col(User).update_one(
            {"_id": instructor.id}, {"$push": {"courses": course.id}, "$set": {"updatedAt": utcnow()}}
        )
        await _col(Category).update_one({"_id": category_doc.id}, {"$push": {"courses": course.id}})
        return send({"success": True, "data": doc_to_dict(course), "message": "Course Created Successfully"})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Failed to create course", "error": str(exc)}, 500)


@router.post("/editCourse")
async def edit_course(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, files = await get_body(request)
        course = await find_by_id(Course, body.get("courseId"))
        if not course:
            return send({"error": "Course not found"}, 404)

        if files:
            thumbnail = files.get("thumbnailImage")
            if thumbnail is None:
                raise TypeError("Cannot read properties of undefined (reading 'tempFilePath')")
            image = await upload_to_cloudinary(thumbnail, settings.FOLDER_NAME)
            course.thumbnail = image["secure_url"]

        # Only known course fields are applied; everything else in the form is ignored.
        for key, value in body.items():
            if key in ("tag", "instructions"):
                setattr(course, key, _json_list(value))
            elif key == "price":
                course.price = cast_number(value, "price", "Course")
            elif key == "status":
                _check_status(value)
                course.status = value
            elif key == "category":
                course.category = to_oid(value, "Course", "category")
            elif key in ("courseName", "courseDescription", "whatYouWillLearn", "thumbnail"):
                setattr(course, key, value)
        await course.save()

        updated = await Course.get(course.id)
        return send(
            {"success": True, "message": "Course updated successfully", "data": await course_full(updated)}
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


@router.get("/getAllCourses")
async def get_all_courses():
    try:
        courses = await Course.find({"status": "Published"}).to_list()
        data = []
        for course in courses:
            item = doc_to_dict(course)
            item = {
                k: item[k]
                for k in ("_id", "courseName", "price", "thumbnail", "instructor", "ratingAndReviews")
                if k in item
            }
            instructor = await User.get(course.instructor)
            item["instructor"] = doc_to_dict(instructor) if instructor else None
            data.append(item)
        return send({"success": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Can't Fetch Course Data", "error": str(exc)}, 404)


@router.post("/getCourseDetails")
async def get_course_details(request: Request):
    try:
        body, _ = await get_body(request)
        course_id = body.get("courseId")
        course = await find_by_id(Course, course_id)
        if not course:
            return send({"success": False, "message": f"Could not find course with id: {course_id}"}, 400)
        details = await course_full(course, hide_video=True)
        total = convert_seconds_to_duration(_total_seconds(details["courseContent"]))
        return send({"success": True, "data": {"courseDetails": details, "totalDuration": total}})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": str(exc)}, 500)


@router.post("/getFullCourseDetails")
async def get_full_course_details(request: Request, current: dict = Depends(auth)):
    try:
        body, _ = await get_body(request)
        course_id = body.get("courseId")
        course = await find_by_id(Course, course_id)
        progress = None
        if course:
            progress = await CourseProgress.find_one(
                CourseProgress.courseID == course.id, CourseProgress.userId == to_oid(current.get("id"), "user")
            )
        if not course:
            return send({"success": False, "message": f"Could not find course with id: {course_id}"}, 400)
        details = await course_full(course)
        total = convert_seconds_to_duration(_total_seconds(details["courseContent"]))
        return send(
            {
                "success": True,
                "data": {
                    "courseDetails": details,
                    "totalDuration": total,
                    "completedVideos": [str(v) for v in progress.completedVideos] if progress else [],
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": str(exc)}, 500)


@router.get("/getInstructorCourses")
async def get_instructor_courses(current: dict = Depends(is_instructor)):
    try:
        courses = await Course.find({"instructor": to_oid(current.get("id"), "user")}).sort("-createdAt").to_list()
        return send({"success": True, "data": [doc_to_dict(c) for c in courses]})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Failed to retrieve instructor courses", "error": str(exc)}, 500)


# SECURITY: only an authenticated instructor may delete a course.
@router.delete("/deleteCourse")
async def delete_course(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, _ = await get_body(request)
        course_id = body.get("courseId")
        course = await find_by_id(Course, course_id)
        if not course:
            return send({"message": "Course not found"}, 404)

        for student_id in course.studentsEnroled:
            await _col(User).update_one({"_id": student_id}, {"$pull": {"courses": course.id}})
        for section_id in course.courseContent:
            section = await Section.get(section_id)
            if section:
                await SubSection.find({"_id": {"$in": section.subSection}}).delete()
            await _col(Section).delete_one({"_id": section_id})
        await course.delete()
        return send({"success": True, "message": "Course deleted successfully"})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Server error", "error": str(exc)}, 500)


# ───────────────────────────── Sections ─────────────────────────────


@router.post("/addSection")
async def create_section(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, _ = await get_body(request)
        section_name, course_id = body.get("sectionName"), body.get("courseId")
        if js_falsy(section_name) or js_falsy(course_id):
            return send({"success": False, "message": "Missing required properties"}, 400)
        section = Section(sectionName=section_name)
        await section.insert()
        course_oid = to_oid(course_id, "Course")
        await _col(Course).update_one({"_id": course_oid}, {"$push": {"courseContent": section.id}})
        updated = await Course.get(course_oid)
        return send(
            {"success": True, "message": "Section created successfully", "updatedCourse": await course_with_content(updated)}
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


@router.post("/updateSection")
async def update_section(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, _ = await get_body(request)
        section = await find_by_id(Section, body.get("sectionId"))
        if section:
            section.sectionName = body.get("sectionName")
            await section.save()
        course = await find_by_id(Course, body.get("courseId"))
        return send(
            {
                "success": True,
                "message": doc_to_dict(section) if section else None,
                "data": await course_with_content(course),
            }
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


@router.post("/deleteSection")
async def delete_section(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, _ = await get_body(request)
        section_id, course_id = to_oid(body.get("sectionId"), "Section"), to_oid(body.get("courseId"), "Course")
        await _col(Course).update_one({"_id": course_id}, {"$pull": {"courseContent": section_id}})
        section = await Section.get(section_id)
        if not section:
            return send({"success": False, "message": "Section not found"}, 404)
        await SubSection.find({"_id": {"$in": section.subSection}}).delete()
        await section.delete()
        course = await Course.get(course_id)
        return send({"success": True, "message": "Section deleted", "data": await course_with_content(course)})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


# ───────────────────────────── Sub-sections ─────────────────────────────


@router.post("/addSubSection")
async def create_sub_section(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, files = await get_body(request)
        section_id, title, description = body.get("sectionId"), body.get("title"), body.get("description")
        video = files.get("video")
        if not files:  # no file was uploaded
            raise TypeError("Cannot read properties of undefined (reading 'video')")
        if js_falsy(section_id) or js_falsy(title) or js_falsy(description) or video is None:
            return send({"success": False, "message": "All Fields are Required"}, 404)

        upload = await upload_to_cloudinary(video, settings.FOLDER_NAME)
        sub = SubSection(
            title=title,
            timeDuration=f"{upload.get('duration')}",
            description=description,
            videoUrl=upload["secure_url"],
        )
        await sub.insert()
        section_oid = to_oid(section_id, "Section")
        await _col(Section).update_one({"_id": section_oid}, {"$push": {"subSection": sub.id}})
        updated = await Section.get(section_oid)
        return send({"success": True, "data": await section_with_subs(updated)})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


@router.post("/updateSubSection")
async def update_sub_section(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, files = await get_body(request)
        sub = await find_by_id(SubSection, body.get("subSectionId"))
        if not sub:
            return send({"success": False, "message": "SubSection not found"}, 404)
        if body.get("title") is not None:
            sub.title = body["title"]
        if body.get("description") is not None:
            sub.description = body["description"]
        if "video" in files:
            upload = await upload_to_cloudinary(files["video"], settings.FOLDER_NAME)
            sub.videoUrl = upload["secure_url"]
            sub.timeDuration = f"{upload.get('duration')}"
        await sub.save()
        section = await find_by_id(Section, body.get("sectionId"))
        return send(
            {"success": True, "message": "Section updated successfully", "data": await section_with_subs(section)}
        )
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "An error occurred while updating the section"}, 500)


@router.post("/deleteSubSection")
async def delete_sub_section(request: Request, current: dict = Depends(is_instructor)):
    try:
        body, _ = await get_body(request)
        sub_id, section_id = to_oid(body.get("subSectionId"), "SubSection"), to_oid(body.get("sectionId"), "Section")
        await _col(Section).update_one({"_id": section_id}, {"$pull": {"subSection": sub_id}})
        deleted = await SubSection.get(sub_id)
        if not deleted:
            return send({"success": False, "message": "SubSection not found"}, 404)
        await deleted.delete()
        section = await Section.get(section_id)
        return send(
            {"success": True, "message": "SubSection deleted successfully", "data": await section_with_subs(section)}
        )
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "An error occurred while deleting the SubSection"}, 500)


# ───────────────────────────── Categories ─────────────────────────────


@router.post("/createCategory")
async def create_category(request: Request, current: dict = Depends(is_admin)):
    try:
        body, _ = await get_body(request)
        name = body.get("name")
        if js_falsy(name):
            return send({"success": False, "message": "All fields are required"}, 400)
        await Category(name=name, description=body.get("description")).insert()
        return send({"success": True, "message": "Categorys Created Successfully"})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": True, "message": str(exc)}, 500)  # (success stays true: the client treats this response shape as a no-op)


@router.get("/showAllCategories")
async def show_all_categories():
    try:
        return send({"success": True, "data": [doc_to_dict(c) for c in await Category.find_all().to_list()]})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": str(exc)}, 500)


async def _published_courses(category: Category) -> list[Course]:
    return [c for c in await fetch_ordered(Course, category.courses) if c.status == "Published"]


@router.post("/getCategoryPageDetails")
async def category_page_details(request: Request):
    try:
        body, _ = await get_body(request)
        category = await find_by_id(Category, body.get("categoryId"))
        if not category:
            return send({"success": False, "message": "Category not found"}, 404)

        selected = doc_to_dict(category)
        courses = await _published_courses(category)
        selected_courses = []
        for course in courses:
            item = doc_to_dict(course)
            reviews = await fetch_ordered(RatingAndReview, course.ratingAndReviews)
            item["ratingAndReviews"] = [doc_to_dict(r) for r in reviews]
            selected_courses.append(item)
        selected["courses"] = selected_courses
        if not selected_courses:
            return send({"success": False, "message": "No courses found for the selected category."}, 404)

        others = await Category.find({"_id": {"$ne": category.id}}).to_list()
        if not others:
            raise TypeError("Cannot read properties of undefined (reading '_id')")
        different = random.choice(others)
        different_dict = doc_to_dict(different)
        different_dict["courses"] = [doc_to_dict(c) for c in await _published_courses(different)]

        most_selling = []
        for cat in await Category.find_all().to_list():
            most_selling.extend(doc_to_dict(c) for c in await _published_courses(cat))
        return send(
            {
                "success": True,
                "data": {
                    "selectedCategory": selected,
                    "differentCategory": different_dict,
                    "mostSellingCourses": most_selling[:10],
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


# ───────────────────────────── Ratings & progress ─────────────────────────────


@router.post("/createRating")
async def create_rating(request: Request, current: dict = Depends(is_student)):
    try:
        body, _ = await get_body(request)
        user_id = to_oid(current.get("id"), "user")
        rating, review, course_id = body.get("rating"), body.get("review"), body.get("courseId")
        course_oid = to_oid(course_id, "Course", "_id")

        enrolled = await Course.find_one({"_id": course_oid, "studentsEnroled": user_id})
        if not enrolled:
            return send({"success": False, "message": "Student is not enrolled in this course"}, 404)
        if await RatingAndReview.find_one({"user": user_id, "course": course_oid}):
            return send({"success": False, "message": "Course already reviewed by user"}, 403)

        if js_falsy(review) or rating is None:
            raise ValueError("RatingAndReview validation failed: rating and review are required")
        doc = RatingAndReview(rating=cast_number(rating, "rating"), review=review, course=course_oid, user=user_id)
        await doc.insert()
        await _col(Course).update_one({"_id": course_oid}, {"$push": {"ratingAndReviews": doc.id}})
        return send(
            {"success": True, "message": "Rating and review created successfully", "ratingReview": doc_to_dict(doc)},
            201,
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Internal server error", "error": str(exc)}, 500)


@router.get("/getAverageRating")
async def get_average_rating(request: Request):
    try:
        body, _ = await get_body(request)
        course_id = body.get("courseId") or request.query_params.get("courseId")
        if course_id is None:
            return send({"success": True, "averageRating": 0})  # no course id supplied: nothing to average
        pipeline = [
            {"$match": {"course": _agg_oid(course_id)}},
            {"$group": {"_id": None, "averageRating": {"$avg": "$rating"}}},
        ]
        result = await _col(RatingAndReview).aggregate(pipeline).to_list(1)
        return send({"success": True, "averageRating": result[0]["averageRating"] if result else 0})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send(
            {"success": False, "message": "Failed to retrieve the rating for the course", "error": str(exc)}, 500
        )


@router.get("/getReviews")
async def get_all_rating_review():
    try:
        reviews = await RatingAndReview.find_all().sort("-rating").to_list()
        data = []
        for review in reviews:
            item = doc_to_dict(review)
            user = await User.get(review.user)
            course = await Course.get(review.course)
            item["user"] = (
                {k: v for k, v in doc_to_dict(user).items() if k in ("_id", "firstName", "lastName", "email", "image")}
                if user
                else None
            )
            item["course"] = {"_id": str(course.id), "courseName": course.courseName} if course else None
            data.append(item)
        return send({"success": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send(
            {"success": False, "message": "Failed to retrieve the rating and review for the course", "error": str(exc)},
            500,
        )


@router.post("/updateCourseProgress")
async def update_course_progress(request: Request, current: dict = Depends(is_student)):
    try:
        body, _ = await get_body(request)
        subsection_id, course_id = body.get("subsectionId"), body.get("courseId")
        user_id = to_oid(current.get("id"), "user")
        sub = await find_by_id(SubSection, subsection_id)
        if not sub:
            return send({"error": "Invalid subsection"}, 404)
        progress = await CourseProgress.find_one(
            {"courseID": to_oid(course_id, "courseProgress", "courseID"), "userId": user_id}
        )
        if not progress:
            return send({"success": False, "message": "Course progress Does Not Exist"}, 404)
        if sub.id in progress.completedVideos:
            return send({"error": "Subsection already completed"}, 400)
        progress.completedVideos.append(sub.id)
        await progress.save()
        return send({"message": "Course progress updated"})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"error": "Internal server error"}, 500)
