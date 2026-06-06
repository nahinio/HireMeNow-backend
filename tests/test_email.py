from unittest.mock import AsyncMock, patch

from app.services.email import (
    build_email_banner_inline_attachment,
    build_email_banner_public_url,
    build_password_reset_url,
    render_password_reset_html,
    send_password_reset_email,
)


def test_build_password_reset_url_appends_token_query():
    url = build_password_reset_url("http://localhost:5173/reset-password", "abc/123")
    assert url.startswith("http://localhost:5173/reset-password?")
    assert "token=abc%2F123" in url
    assert url.endswith("#/reset-password")


def test_build_password_reset_url_replaces_existing_token():
    url = build_password_reset_url(
        "http://localhost:5173/reset-password?token=old",
        "new-token",
    )
    assert "token=new-token" in url
    assert "token=old" not in url
    assert "#/reset-password" in url


def test_build_password_reset_url_uses_production_frontend():
    url = build_password_reset_url("http://hiremenow.nahinio.xyz/", "reset-me")
    assert url.startswith("http://hiremenow.nahinio.xyz/?")
    assert "token=reset-me" in url
    assert url.endswith("#/reset-password")


def test_build_email_banner_public_url():
    url = build_email_banner_public_url()
    assert url.endswith("/static/email/HireMeNow.png")


def test_build_email_banner_inline_attachment():
    attachment = build_email_banner_inline_attachment()
    assert attachment["filename"] == "HireMeNow.png"
    assert attachment["content_id"] == "hiremenow-banner"
    assert attachment["content_type"] == "image/png"
    assert attachment["content"]


def test_render_password_reset_html_uses_cid_for_resend():
    html = render_password_reset_html("http://hiremenow.nahinio.xyz/?token=test", use_inline_banner=True)
    assert 'href="http://hiremenow.nahinio.xyz/?token=test"' in html
    assert 'src="cid:hiremenow-banner"' in html
    assert "Set new password" in html
    assert "Sent by <span>HireMeNow</span>" in html


def test_render_password_reset_html_uses_public_url_for_smtp():
    html = render_password_reset_html("http://hiremenow.nahinio.xyz/?token=test", use_inline_banner=False)
    assert "/static/email/HireMeNow.png" in html


async def test_send_password_reset_email_uses_resend_api_with_inline_banner():
    with (
        patch("app.services.email.get_settings") as mock_settings,
        patch(
            "app.services.email._send_via_resend_api",
            new_callable=AsyncMock,
        ) as mock_resend,
    ):
        settings = mock_settings.return_value
        settings.email_is_configured.return_value = True
        settings.resend_api_key.return_value = "re_test_key"
        settings.smtp_is_configured.return_value = False
        settings.FRONTEND_RESET_URL = "http://hiremenow.nahinio.xyz/"
        settings.APP_NAME = "HireMeNow"
        settings.PASSWORD_RESET_EXPIRE_MINUTES = 60

        await send_password_reset_email("user@example.com", "secret-token")

    mock_resend.assert_awaited_once()
    assert mock_resend.await_args.kwargs["to_email"] == "user@example.com"
    assert mock_resend.await_args.kwargs["attachments"][0]["content_id"] == "hiremenow-banner"
    assert "cid:hiremenow-banner" in mock_resend.await_args.kwargs["html_body"]
