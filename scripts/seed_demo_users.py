"""Seed demo freelancer and client accounts for local/staging demos."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from cat_freelancer_data import cat_avatar_url, cat_display_name  # noqa: E402
from freelancer_public_demo_data import (  # noqa: E402
    DEMO_RESUME_URL,
    demo_contact_email,
    demo_github_url,
    demo_linkedin_url,
    demo_portfolio_url,
)

from app.core.security import hash_password  # noqa: E402
from app.db.engine import async_session_maker  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import ClientProfile, FreelancerProfile, User  # noqa: E402

DEMO_PASSWORD = "demo123456"
FREELANCER_COUNT = 15
CLIENT_COUNT = 15

FREELANCER_BIOS = [
    "Full-stack developer focused on React and Node.",
    "UI/UX designer with 5+ years of product experience.",
    "Python backend engineer — APIs, data pipelines, automation.",
    "Mobile developer (React Native & Flutter).",
    "DevOps specialist — AWS, Docker, CI/CD.",
    "Content writer and technical copywriter.",
    "Data analyst with SQL, Python, and visualization skills.",
    "WordPress and Shopify developer.",
    "Video editor and motion graphics artist.",
    "SEO consultant and growth marketer.",
    "Graphic designer for brands and startups.",
    "QA engineer — manual and automated testing.",
    "Blockchain developer — Solidity and Web3.",
    "Project manager with agile delivery experience.",
    "Machine learning engineer — NLP and computer vision.",
]

CLIENT_COMPANIES = [
    "Nova Labs",
    "Pixel & Co",
    "Summit Ventures",
    "Blue Harbor Tech",
    "Greenfield Studio",
    "Atlas Digital",
    "Brightline Media",
    "CoreStack Systems",
    "Horizon Works",
    "Lumen Agency",
    "Northwind Apps",
    "Orbit Commerce",
    "PrimeRoute LLC",
    "Silverline Creative",
    "Vertex Solutions",
]

CLIENT_BIOS = [
    "Early-stage startup building SaaS tools.",
    "Design agency working with global brands.",
    "E-commerce company scaling fast.",
    "B2B software consultancy.",
    "Creative studio for web and mobile products.",
    "Fintech team hiring remote talent.",
    "Healthcare tech with a mission-driven culture.",
    "Marketing agency — always looking for freelancers.",
    "EdTech platform for professional courses.",
    "Real estate tech modernizing listings.",
    "Nonprofit building community apps.",
    "Logistics startup optimizing last-mile delivery.",
    "Media company producing digital content.",
    "AI product team shipping fast iterations.",
    "Retail brand expanding online presence.",
]


async def seed_role(
    session,
    *,
    role: UserRole,
    count: int,
    email_template: str,
    profile_factory,
) -> tuple[int, int]:
    created = 0
    skipped = 0

    for i in range(1, count + 1):
        email = email_template.format(i=i)
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            skipped += 1
            continue

        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=role,
        )
        session.add(user)
        await session.flush()
        session.add(profile_factory(user.id, i))
        created += 1

    return created, skipped


async def main() -> None:
    async with async_session_maker() as session:
        f_created, f_skipped = await seed_role(
            session,
            role=UserRole.freelancer,
            count=FREELANCER_COUNT,
            email_template="demofreelancer{i}@gmail.com",
            profile_factory=lambda user_id, i: FreelancerProfile(
                user_id=user_id,
                display_name=cat_display_name(i),
                bio=FREELANCER_BIOS[(i - 1) % len(FREELANCER_BIOS)],
                profile_picture_url=cat_avatar_url(i),
                available_for_work=i % 4 != 0,
                contact_email=demo_contact_email(f"demofreelancer{i}@gmail.com"),
                linkedin_url=demo_linkedin_url(cat_display_name(i)),
                github_url=demo_github_url(cat_display_name(i)),
                portfolio_url=demo_portfolio_url(cat_display_name(i)),
                resume_url=DEMO_RESUME_URL,
            ),
        )

        c_created, c_skipped = await seed_role(
            session,
            role=UserRole.client,
            count=CLIENT_COUNT,
            email_template="democlient{i}@gmail.com",
            profile_factory=lambda user_id, i: ClientProfile(
                user_id=user_id,
                company_name=CLIENT_COMPANIES[(i - 1) % len(CLIENT_COMPANIES)],
                bio=CLIENT_BIOS[(i - 1) % len(CLIENT_BIOS)],
            ),
        )

        await session.commit()

    print("Demo accounts seeded successfully.")
    print(f"  Freelancers: {f_created} created, {f_skipped} skipped")
    print(f"  Clients:     {c_created} created, {c_skipped} skipped")
    print(f"  Password (all): {DEMO_PASSWORD}")
    print("  Examples:")
    print("    demofreelancer1@gmail.com")
    print("    democlient1@gmail.com")


if __name__ == "__main__":
    asyncio.run(main())
