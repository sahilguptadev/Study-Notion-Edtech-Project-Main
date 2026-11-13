import math

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core.deps import auth, is_instructor
from app.models import Course, CourseProgress, Profile, User
from app.models.base import utcnow
from app.services.population import fetch_ordered, sections_tree, user_with_profile
from app.utils.duration import convert_seconds_to_duration, parse_int
from app.utils.http import get_body, send, log_error
from app.utils.objid import CastError, find_by_id, to_oid
from app.utils.serialize import doc_to_dict
from app.utils.uploader import upload_to_cloudinary

router = APIRouter()


def _contact_number(value):
    """Number cast: '' -> null, numeric string -> number, else CastError."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        raise CastError(
            f'Profile validation failed: contactNumber: Cast to Number failed for value "{value}" (type string) at path "contactNumber"'
        )


@router.put("/updateProfile")
async def update_profile(request: Request, current: dict = Depends(auth)):
    try:
        body, _ = await get_body(request)
        user = await find_by_id(User, current.get("id"))
        profile = await Profile.get(user.additionalDetails)

        user.firstName = body.get("firstName", "")
        user.lastName = body.get("lastName", "")
        user.updatedAt = utcnow()

        about = body.get("about", "")
        profile.dateOfBirth = body.get("dateOfBirth", "")
        profile.about = about.strip() if isinstance(about, str) else about
        profile.contactNumber = _contact_number(body.get("contactNumber", ""))
        profile.gender = body.get("gender", "")
        await profile.save()
        await user.save()

        return send(
            {"success": True, "message": "Profile updated successfully", "updatedUserDetails": await user_with_profile(user)}
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "error": str(exc)}, 500)


@router.delete("/deleteProfile")
async def delete_account(current: dict = Depends(auth)):
    try:
        user = await find_by_id(User, current.get("id"))
        if not user:
            return send({"success": False, "message": "User not found"}, 404)
        await Profile.find_one({"_id": user.additionalDetails}).delete()
        for course_id in user.courses:
            await Course.get_motor_collection().update_one(
                {"_id": course_id}, {"$pull": {"studentsEnroled": user.id}}
            )
        await user.delete()
        await CourseProgress.find({"userId": user.id}).delete()
        return send({"success": True, "message": "User deleted successfully"})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "User Cannot be deleted successfully"}, 500)


@router.get("/getUserDetails")
async def get_all_user_details(current: dict = Depends(auth)):
    try:
        user = await find_by_id(User, current.get("id"))
        return send(
            {"success": True, "message": "User Data fetched successfully", "data": await user_with_profile(user)}
        )
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": str(exc)}, 500)


@router.put("/updateDisplayPicture")
async def update_display_picture(request: Request, current: dict = Depends(auth)):
    try:
        _, files = await get_body(request)
        picture = files.get("displayPicture")
        if picture is None:
            raise TypeError("Cannot read properties of undefined (reading 'displayPicture')")
        image = await upload_to_cloudinary(picture, settings.FOLDER_NAME, 1000, 1000)
        user = await find_by_id(User, current.get("id"))
        user.image = image["secure_url"]
        user.updatedAt = utcnow()
        await user.save()
        return send({"success": True, "message": "Image Updated successfully", "data": doc_to_dict(user)})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": str(exc)}, 500)


def _round2(x: float) -> float:
    return math.floor(x * 100 + 0.5) / 100  # JS Math.round (half up)


@router.get("/getEnrolledCourses")
async def get_enrolled_courses(current: dict = Depends(auth)):
    try:
        user_id = to_oid(current.get("id"), "user")
        user = await User.get(user_id)
        courses = await fetch_ordered(Course, user.courses)
        result = []
        for course in courses:
            data = doc_to_dict(course)
            data["courseContent"] = content = await sections_tree(course.courseContent)
            total_seconds, lecture_count = 0, 0
            for section in content:
                total_seconds += sum(parse_int(s.get("timeDuration")) for s in section["subSection"])
                data["totalDuration"] = convert_seconds_to_duration(total_seconds)
                lecture_count += len(section["subSection"])
            progress = await CourseProgress.find_one(
                CourseProgress.courseID == course.id, CourseProgress.userId == user_id
            )
            completed = len(progress.completedVideos) if progress else None
            if lecture_count == 0:
                data["progressPercentage"] = 100
            elif completed is None:
                data["progressPercentage"] = None  # JS: undefined / n -> NaN -> null
            else:
                data["progressPercentage"] = _round2(completed / lecture_count * 100)
            result.append(data)
        return send({"success": True, "data": result})
    except Exception as exc:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": str(exc)}, 500)


@router.get("/instructorDashboard")
async def instructor_dashboard(current: dict = Depends(is_instructor)):
    try:
        courses = await Course.find({"instructor": to_oid(current.get("id"), "user")}).to_list()
        data = []
        for course in courses:
            students = len(course.studentsEnroled)
            data.append(
                {
                    "_id": str(course.id),
                    "courseName": course.courseName,
                    "courseDescription": course.courseDescription,
                    "totalStudentsEnrolled": students,
                    "totalAmountGenerated": students * (course.price if course.price is not None else math.nan),
                }
            )
        return send({"courses": data})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"message": "Server Error"}, 500)
