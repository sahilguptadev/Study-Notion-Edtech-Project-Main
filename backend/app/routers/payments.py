import asyncio
import hmac
import random

import razorpay
from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core.deps import is_student
from app.core.security import razorpay_signature
from app.models import Course, CourseProgress, User
from app.models.base import utcnow
from app.utils.http import get_body, js_falsy, send, log_error
from app.utils.mail import mail_sender, render_template
from app.utils.objid import find_by_id, to_oid

router = APIRouter()


def _razorpay() -> razorpay.Client:
    return razorpay.Client(auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET))


@router.post("/capturePayment")
async def capture_payment(request: Request, current: dict = Depends(is_student)):
    body, _ = await get_body(request)
    courses = body.get("courses")
    user_id = to_oid(current.get("id"), "user")
    if not isinstance(courses, list):
        return send({"success": False, "message": "Please Provide Course ID"}, 500)
    if len(courses) == 0:
        return send({"success": False, "message": "Please Provide Course ID"})

    total = 0
    for course_id in courses:
        try:
            course = await find_by_id(Course, course_id)
            if not course:
                return send({"success": False, "message": "Could not find the Course"})
            if user_id in course.studentsEnroled:
                return send({"success": False, "message": "Student is already Enrolled"})
            total += course.price or 0
        except Exception as exc:  # noqa: BLE001
            return send({"success": False, "message": str(exc)}, 500)

    options = {"amount": int(round(total * 100)), "currency": "INR", "receipt": str(random.random())}
    try:
        order = await asyncio.to_thread(_razorpay().order.create, options)
        return send({"success": True, "data": order})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Could not initiate order."}, 500)


async def _enroll_students(courses, user_id):
    """Returns an error response, or None when every course was enrolled."""
    if not courses or not user_id:
        return send({"success": False, "message": "Please Provide Course ID and User ID"}, 400)
    user_oid = to_oid(user_id, "user")
    for course_id in courses:
        try:
            course_oid = to_oid(course_id, "Course")
            result = await Course.get_motor_collection().update_one(
                {"_id": course_oid}, {"$push": {"studentsEnroled": user_oid}}
            )
            if result.matched_count == 0:
                return send({"success": False, "error": "Course not found"}, 500)
            course = await Course.get(course_oid)

            progress = CourseProgress(courseID=course_oid, userId=user_oid, completedVideos=[])
            await progress.insert()
            await User.get_motor_collection().update_one(
                {"_id": user_oid},
                {"$push": {"courses": course_oid, "courseProgress": progress.id}, "$set": {"updatedAt": utcnow()}},
            )
            student = await User.get(user_oid)
            await mail_sender(
                student.email,
                f"Successfully Enrolled into {course.courseName}",
                render_template(
                    "courseEnrollmentEmail",
                    courseName=course.courseName,
                    name=f"{student.firstName} {student.lastName}",
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return send({"success": False, "error": str(exc)}, 400)
    return None


@router.post("/verifyPayment")
async def verify_payment(request: Request, current: dict = Depends(is_student)):
    body, _ = await get_body(request)
    order_id, payment_id = body.get("razorpay_order_id"), body.get("razorpay_payment_id")
    signature, courses = body.get("razorpay_signature"), body.get("courses")
    user_id = current.get("id")

    if any(js_falsy(v) for v in (order_id, payment_id, signature, courses, user_id)):
        return send({"success": False, "message": "Payment Failed"})

    expected = razorpay_signature(str(order_id), str(payment_id))
    if hmac.compare_digest(expected, str(signature)):
        error = await _enroll_students(courses, user_id)
        if error is not None:
            return error
        return send({"success": True, "message": "Payment Verified"})
    return send({"success": False, "message": "Payment Failed"})


@router.post("/sendPaymentSuccessEmail")
async def send_payment_success_email(request: Request, current: dict = Depends(is_student)):
    body, _ = await get_body(request)
    order_id, payment_id, amount = body.get("orderId"), body.get("paymentId"), body.get("amount")
    user_id = current.get("id")
    if any(js_falsy(v) for v in (order_id, payment_id, amount, user_id)):
        return send({"success": False, "message": "Please provide all the details"}, 400)
    try:
        student = await find_by_id(User, user_id)
        amount_rupees = amount / 100
        await mail_sender(
            student.email,
            "Payment Received",
            render_template(
                "paymentSuccessEmail",
                name=f"{student.firstName} {student.lastName}",
                amount=int(amount_rupees) if float(amount_rupees).is_integer() else amount_rupees,
                orderId=order_id,
                paymentId=payment_id,
            ),
        )
        # Acknowledge the request once the email has been handed off.
        return send({"success": True, "message": "Payment success email sent"})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Could not send email"}, 400)
