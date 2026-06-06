from unittest.mock import AsyncMock, patch

from app.services.email import (
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


def test_build_password_reset_url_adds_hash_route_for_spa_root():
    url = build_password_reset_url("http://127.0.0.1:5500/", "reset-me")
    assert url.startswith("http://127.0.0.1:5500/?")
    assert "token=reset-me" in url
    assert url.endswith("#/reset-password")


def test_render_password_reset_html_uses_design_template():
    html = render_password_reset_html("http://127.0.0.1:5500/?token=test")
    assert 'href="http://127.0.0.1:5500/?token=test"' in html
    assert "Set new password" in html
    assert 'src="data:image/png;base64,' in html
    assert "Sent by <span>HireMeNow</span>" in html


async def test_send_password_reset_email_uses_resend_api():
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
        settings.FRONTEND_RESET_URL = "http://127.0.0.1:5500/"
        settings.APP_NAME = "HireMeNow"
        settings.PASSWORD_RESET_EXPIRE_MINUTES = 60

        await send_password_reset_email("user@example.com", "secret-token")

    mock_resend.assert_awaited_once()
    assert mock_resend.await_args.kwargs["to_email"] == "user@example.com"
