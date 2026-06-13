"""Rename all freelancer profiles to cat names and set demo cat avatars."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.db.engine import async_session_maker  # noqa: E402
from app.models.user import FreelancerProfile, User  # noqa: E402
from cat_freelancer_data import cat_avatar_url, cat_display_name  # noqa: E402


async def main() -> None:
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

        for i, (profile, email) in enumerate(rows, start=1):
            name = cat_display_name(i)
            avatar = cat_avatar_url(i)
            profile.display_name = name
            profile.profile_picture_url = avatar
            print(f"  {email} -> {name}")

        await session.commit()

    print(f"\nUpdated {len(rows)} freelancer(s) with cat names and profile pictures.")


if __name__ == "__main__":
    asyncio.run(main())
