from app.services.email import build_password_reset_url, render_password_reset_html


def test_build_password_reset_url_appends_token_query():
    url = build_password_reset_url("http://localhost:5173/reset-password", "abc/123")
    assert url.startswith("http://localhost:5173/reset-password?")
    assert "token=abc%2F123" in url


def test_build_password_reset_url_replaces_existing_token():
    url = build_password_reset_url(
        "http://localhost:5173/reset-password?token=old",
        "new-token",
    )
    assert "token=new-token" in url
    assert "token=old" not in url


def test_render_password_reset_html_uses_design_template():
    html = render_password_reset_html("http://127.0.0.1:5500/?token=test")
    assert 'href="http://127.0.0.1:5500/?token=test"' in html
    assert "Set new password" in html
    assert "https://i.imgur.com/0Td5v8y.png" in html
    assert "Sent by <span>HireMeNow</span>" in html
