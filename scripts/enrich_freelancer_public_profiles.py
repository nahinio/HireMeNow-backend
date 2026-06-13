"""Fill missing public contact, links, resume, and portfolio data on freelancer profiles."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.db.engine import async_session_maker  # noqa: E402
from app.models.user import FreelancerProfile, PortfolioLink, User  # noqa: E402
from freelancer_public_demo_data import (  # noqa: E402
    DEMO_RESUME_URL,
    demo_contact_email,
    demo_github_url,
    demo_linkedin_url,
    demo_portfolio_links,
    demo_portfolio_url,
)


async def main() -> None:
    updated_profiles = 0
    added_links = 0

    async with async_session_maker() as session:
        result = await session.execute(
            select(FreelancerProfile, User.email)
            .join(User, User.id == FreelancerProfile.user_id)
            .order_by(User.created_at, User.email)
        )
        rows = result.all()

        if not rows:
            print("No freelancer profiles found.")
            return

        for profile, account_email in rows:
            changed = False
            name = profile.display_name

            if not profile.contact_email:
                profile.contact_email = demo_contact_email(account_email)
                changed = True
            if not profile.linkedin_url:
                profile.linkedin_url = demo_linkedin_url(name)
                changed = True
            if not profile.github_url:
                profile.github_url = demo_github_url(name)
                changed = True
            if not profile.portfolio_url:
                profile.portfolio_url = demo_portfolio_url(name)
                changed = True
            if not profile.resume_url:
                profile.resume_url = DEMO_RESUME_URL
                changed = True

            if changed:
                updated_profiles += 1
                print(f"  Updated profile fields: {name} ({account_email})")

            existing_links = await session.execute(
                select(PortfolioLink).where(PortfolioLink.profile_id == profile.id)
            )
            if not existing_links.scalars().first():
                for label, url, position in demo_portfolio_links(name):
                    session.add(
                        PortfolioLink(
                            profile_id=profile.id,
                            label=label,
                            url=url,
                            position=position,
                        )
                    )
                    added_links += 1
                print(f"  Added portfolio links: {name}")

        await session.commit()

    print(
        f"\nEnriched {updated_profiles} profile(s) and added {added_links} portfolio link(s)."
    )


if __name__ == "__main__":
    asyncio.run(main())
