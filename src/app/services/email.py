import asyncio
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
RESEND_API_URL = "https://api.resend.com/emails"


def build_password_reset_url(frontend_reset_url: str, token: str) -> str:
    parsed = urlparse(frontend_reset_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["token"] = [token]
    clean_query = urlencode({key: values[0] for key, values in query.items()}, doseq=False)

    fragment = parsed.fragment
    if not fragment:
        fragment = "/reset-password"

    return urlunparse(parsed._replace(query=clean_query, fragment=fragment))


def render_password_reset_html(reset_url: str) -> str:
    template = (EMAIL_TEMPLATE_DIR / "password_reset.html").read_text(encoding="utf-8")
    return template.replace("{{ reset_url }}", reset_url)


def render_password_reset_text(reset_url: str, app_name: str, expire_minutes: int) -> str:
    return (
        f"Reset your {app_name} password\n\n"
        "We received a request to reset the password for your account. "
        f"Open this link to set a new one (expires in {expire_minutes} minutes):\n"
        f"{reset_url}\n\n"
        "If you didn't request a password reset, please ignore this email.\n\n"
        f"Sent by {app_name}"
    )


def _send_smtp_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    settings = get_settings()
    if not settings.SMTP_HOST or not settings.EMAIL_FROM:
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    if settings.SMTP_USE_TLS:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as client:
            client.ehlo()
            client.starttls()
            client.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            client.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as client:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            client.send_message(message)


async def _send_via_resend_api(
    *,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    settings = get_settings()
    api_key = settings.resend_api_key()
    if not api_key or not settings.EMAIL_FROM:
        raise RuntimeError("Resend API is not configured")

    payload: dict[str, object] = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if html_body:
        payload["html"] = html_body

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("message", detail)
            except Exception:
                pass
            raise RuntimeError(f"Resend API error ({response.status_code}): {detail}")


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    settings = get_settings()
    if not settings.email_is_configured():
        raise RuntimeError("Email is not fully configured")

    reset_url = build_password_reset_url(settings.FRONTEND_RESET_URL, reset_token)
    expire_minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES
    subject = f"Reset your {settings.APP_NAME} password"
    body = render_password_reset_text(reset_url, settings.APP_NAME, expire_minutes)
    html_body = render_password_reset_html(reset_url)

    if settings.resend_api_key():
        await _send_via_resend_api(
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body,
        )
    elif settings.smtp_is_configured():
        await asyncio.to_thread(
            _send_smtp_email,
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body,
        )
    else:
        raise RuntimeError("No email delivery method configured")

    logger.info("Password reset email sent to %s", to_email)
