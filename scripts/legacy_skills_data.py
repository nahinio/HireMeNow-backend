"""Skills that may exist without quizzes — used for job tagging and legacy listings.

These names are not in skills_quiz_data.py. They are typically created via Admin → Skills
(POST /admin/skills) or restored with scripts/seed_legacy_skills.py.

Running reseed_skills.py does NOT remove these skills.
"""

from __future__ import annotations

from typing import TypedDict


class LegacySkill(TypedDict):
    name: str
    description: str


# Older HireMeNow databases often include these alongside the catalog skills from reseed_skills.py.
LEGACY_SKILLS: list[LegacySkill] = [
    {
        "name": "React",
        "description": "React library for building user interfaces (legacy skill tag).",
    },
    {
        "name": "Dhon",
        "description": "Custom skill tag (legacy).",
    },
    {
        "name": "HTML & CSS",
        "description": "HTML markup and CSS styling (legacy skill tag).",
    },
    {
        "name": "JavaScript",
        "description": "JavaScript programming (legacy skill tag).",
    },
    {
        "name": "Node.js",
        "description": "Node.js server-side JavaScript (legacy skill tag).",
    },
    {
        "name": "Python",
        "description": "Python programming (legacy skill tag).",
    },
    {
        "name": "ReactSkill",
        "description": "React-related skill tag (legacy).",
    },
]
