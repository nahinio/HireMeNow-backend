"""Ensure legacy skills (no quiz required) exist in the database without removing anything."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.db.engine import async_session_maker  # noqa: E402
from app.models.skill import Skill  # noqa: E402
from app.models.user import User  # noqa: E402
from legacy_skills_data import LEGACY_SKILLS  # noqa: E402

ADMIN_EMAIL = "admin@hiremenow.com"


async def main() -> None:
    created = 0
    skipped = 0

    async with async_session_maker() as session:
        admin = (
            await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if admin is None:
            raise SystemExit(f"Admin user not found: {ADMIN_EMAIL}")

        for item in LEGACY_SKILLS:
            existing = (
                await session.execute(
                    select(Skill).where(func.lower(Skill.name) == item["name"].lower())
                )
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue

            session.add(
                Skill(
                    name=item["name"],
                    description=item["description"],
                    is_active=True,
                    created_by=admin.id,
                )
            )
            created += 1

        await session.commit()

    print("Legacy skills seed complete.")
    print(f"  Created: {created}")
    print(f"  Already present: {skipped}")
    print(f"  Catalog: {len(LEGACY_SKILLS)} legacy skill names defined in legacy_skills_data.py")


if __name__ == "__main__":
    asyncio.run(main())
