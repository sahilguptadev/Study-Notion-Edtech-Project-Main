from fastapi import APIRouter, Request

from app.utils.http import get_body, send, log_error
from app.utils.mail import mail_sender, render_template

router = APIRouter()


@router.post("/contact")
async def contact_us(request: Request):
    body, _ = await get_body(request)
    try:
        html = render_template(
            "contactFormRes",
            email=body.get("email"),
            firstname=body.get("firstname"),
            lastname=body.get("lastname"),
            message=body.get("message"),
            phoneNo=body.get("phoneNo"),
            countrycode=body.get("countrycode"),
        )
        await mail_sender(body.get("email"), "Your Data send successfully", html)
        return send({"success": True, "message": "Email send successfully"})
    except Exception:  # noqa: BLE001
        log_error()
        return send({"success": False, "message": "Something went wrong..."})
