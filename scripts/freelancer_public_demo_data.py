"""Demo contact, links, and resume data for public freelancer profiles."""

from __future__ import annotations

import re

DEMO_RESUME_URL = (
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
)


def demo_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "freelancer"


def demo_contact_email(account_email: str) -> str:
    return account_email.strip()


def demo_linkedin_url(display_name: str) -> str:
    return f"https://linkedin.com/in/{demo_slug(display_name)}"


def demo_github_url(display_name: str) -> str:
    return f"https://github.com/{demo_slug(display_name)}-dev"


def demo_portfolio_url(display_name: str) -> str:
    return f"https://{demo_slug(display_name)}.example.dev"


def demo_portfolio_links(display_name: str) -> list[tuple[str, str, int]]:
    slug = demo_slug(display_name)
    return [
        ("Featured project", f"https://github.com/{slug}/showcase", 0),
        ("Case study", f"https://{slug}.example.dev/work", 1),
    ]
