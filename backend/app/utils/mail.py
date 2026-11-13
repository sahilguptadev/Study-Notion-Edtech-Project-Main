import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.config import settings

log = logging.getLogger("studynotion.mail")
TEMPLATES = Path(__file__).resolve().parent.parent / "mail_templates"


def render_template(template: str, /, **values) -> str:
    html = (TEMPLATES / f"{template}.html").read_text(encoding="utf-8")
    for key, val in values.items():
        html = html.replace("{{" + key + "}}", str(val))
    return html


def _send_sync(to: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["From"] = f'"Studynotion | CodeHelp" <{settings.MAIL_USER}>'
    msg["To"] = str(to)
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT, timeout=15) as smtp:
        smtp.ehlo()
        if smtp.has_extn("starttls"):
            smtp.starttls()
            smtp.ehlo()
        if settings.MAIL_USER:
            smtp.login(settings.MAIL_USER, settings.MAIL_PASS)
        smtp.sendmail(settings.MAIL_USER, [str(to)], msg.as_string())


async def mail_sender(email: str, title: str, body: str) -> bool:
    """Send an HTML email. Never raises: failures are only logged."""
    try:
        await asyncio.to_thread(_send_sync, email, title, body)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("mail send failed: %s", exc)
        return False
