"""Seed open demo job listings across multiple demo client accounts."""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.db.engine import async_session_maker  # noqa: E402
from app.models.enums import JobStatus, UserRole  # noqa: E402
from app.models.job import Job, JobRequiredSkill  # noqa: E402
from app.models.skill import Skill  # noqa: E402
from app.models.user import ClientProfile, User  # noqa: E402

# Stable public image URLs (Unsplash — tech / workspace themed)
THUMBNAILS = {
    "frontend": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800&h=450&fit=crop",
    "react": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&h=450&fit=crop",
    "javascript": "https://images.unsplash.com/photo-1627398242454-45a1465c2479?w=800&h=450&fit=crop",
    "python": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&h=450&fit=crop",
    "api": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800&h=450&fit=crop",
    "cpp": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&h=450&fit=crop",
    "ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=450&fit=crop",
    "llm": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&h=450&fit=crop",
    "design": "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=450&fit=crop",
    "team": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&h=450&fit=crop",
    "remote": "https://images.unsplash.com/photo-1587614382346-4b42c2b87f42?w=800&h=450&fit=crop",
    "data": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=450&fit=crop",
    "ecommerce": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800&h=450&fit=crop",
    "fintech": "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=800&h=450&fit=crop",
    "health": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800&h=450&fit=crop",
    "mobile": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=800&h=450&fit=crop",
}

# Each entry must include client_email matching seed_demo_users.py (democlient{N}@gmail.com)
DEMO_JOBS: list[dict[str, Any]] = [
    # ── democlient1 — Nova Labs ──
    {
        "client_email": "democlient1@gmail.com",
        "title": "Senior React Frontend Engineer",
        "skills": ["ReactJS", "Vanilla Javascript"],
        "thumbnail": "react",
        "salary": 95000,
        "about_role": "Join Nova Labs to build the next generation of our hiring platform UI. You will own feature delivery across dashboards, job flows, and real-time messaging surfaces.",
        "responsibilities": "Ship accessible React components, integrate REST APIs, write unit tests, and collaborate with design on responsive layouts.",
        "requirements_education": "BS in Computer Science or equivalent practical experience.",
        "requirements_experience": "3+ years building production React apps.",
        "requirements_additional": "Comfortable with Git, CI/CD, and cross-browser testing.",
        "other_benefits": "Remote-friendly, learning stipend, flexible hours.",
        "company_description": "Nova Labs builds tools that connect talented freelancers with growing companies.",
    },
    {
        "client_email": "democlient1@gmail.com",
        "title": "FastAPI Backend Engineer",
        "skills": ["FastAPI (Python)"],
        "thumbnail": "api",
        "salary": 105000,
        "about_role": "Nova Labs is scaling its API layer. You will design REST endpoints, authentication flows, and background jobs powering our marketplace.",
        "responsibilities": "Develop FastAPI routes, write SQLAlchemy models, add tests, and document APIs with OpenAPI.",
        "requirements_education": "BS in CS or equivalent.",
        "requirements_experience": "3+ years Python backend; 1+ year with FastAPI or similar.",
        "requirements_additional": "PostgreSQL, async patterns, secure API design.",
        "other_benefits": "Stock options, remote-first team.",
        "company_description": "Nova Labs ships reliable hiring infrastructure for high-growth teams.",
    },
    {
        "client_email": "democlient1@gmail.com",
        "title": "Agentic AI Integration Engineer",
        "skills": ["Agentic AI", "LLM Basics"],
        "thumbnail": "ai",
        "salary": 130000,
        "about_role": "Nova Labs is experimenting with AI-assisted job matching and candidate screening agents.",
        "responsibilities": "Design agent workflows, integrate LLM providers, build evaluation harnesses, and ship guardrails.",
        "requirements_education": "ML/CS background or strong applied AI portfolio.",
        "requirements_experience": "Hands-on with LLM APIs, prompting, and agent frameworks.",
        "requirements_additional": "Retrieval, function calling, and observability experience.",
        "other_benefits": "GPU credits, research reading time.",
        "company_description": "Nova Labs explores practical AI for hiring workflows.",
    },
    # ── democlient2 — Pixel & Co ──
    {
        "client_email": "democlient2@gmail.com",
        "title": "Vanilla JavaScript UI Developer",
        "skills": ["Vanilla Javascript", "HTML-CSS"],
        "thumbnail": "javascript",
        "salary": 72000,
        "about_role": "Pixel & Co needs a frontend specialist for marketing sites and lightweight embeddable widgets for global brand clients.",
        "responsibilities": "Build interactive landing pages, optimize performance, implement design systems in plain JS/CSS.",
        "requirements_education": "Strong portfolio required.",
        "requirements_experience": "2+ years maintainable vanilla JS in production.",
        "requirements_additional": "DOM APIs, fetch, CSS layout, animation basics.",
        "other_benefits": "Hybrid schedule, hardware budget, studio perks.",
        "company_description": "Pixel & Co is a design-led agency shipping polished web experiences.",
    },
    {
        "client_email": "democlient2@gmail.com",
        "title": "HTML/CSS Marketing Page Builder",
        "skills": ["HTML-CSS"],
        "thumbnail": "design",
        "salary": 58000,
        "about_role": "Pixel & Co is hiring a developer to turn Figma designs into pixel-perfect, responsive campaign pages.",
        "responsibilities": "Slice designs into semantic HTML, responsive CSS, accessibility checks, and reusable pattern libraries.",
        "requirements_education": "Portfolio required.",
        "requirements_experience": "1+ years building marketing and campaign pages.",
        "requirements_additional": "Typography, spacing, mobile-first layouts.",
        "other_benefits": "Paid certifications, collaborative studio culture.",
        "company_description": "Pixel & Co partners with global brands on digital campaigns.",
    },
    {
        "client_email": "democlient2@gmail.com",
        "title": "React Portfolio Site Developer",
        "skills": ["ReactJS", "HTML-CSS"],
        "thumbnail": "frontend",
        "salary": 68000,
        "negotiable": True,
        "about_role": "Pixel & Co builds showcase sites for creative agencies. You will ship fast, animated React experiences.",
        "responsibilities": "Implement motion-friendly React pages, integrate CMS content, and optimize Lighthouse scores.",
        "requirements_education": "Equivalent experience accepted.",
        "requirements_experience": "1+ years React with strong CSS craft.",
        "requirements_additional": "Eye for visual detail and micro-interactions.",
        "other_benefits": "Flexible contract hours, creative team.",
        "company_description": "Pixel & Co crafts memorable brand experiences on the web.",
    },
    # ── democlient3 — Summit Ventures ──
    {
        "client_email": "democlient3@gmail.com",
        "title": "React E-commerce Frontend Engineer",
        "skills": ["ReactJS", "Vanilla Javascript"],
        "thumbnail": "ecommerce",
        "salary": 92000,
        "about_role": "Summit Ventures is scaling a fast-growing e-commerce storefront. You will own checkout flows, product pages, and merchandising tools.",
        "responsibilities": "Build React UI for catalog and cart, integrate payment APIs, improve conversion-focused UX.",
        "requirements_education": "BS or equivalent experience.",
        "requirements_experience": "2+ years React in e-commerce or consumer products.",
        "requirements_additional": "A/B testing familiarity, performance optimization.",
        "other_benefits": "Employee discount, remote options.",
        "company_description": "Summit Ventures is an e-commerce company scaling rapidly across categories.",
    },
    {
        "client_email": "democlient3@gmail.com",
        "title": "FastAPI Inventory API Developer",
        "skills": ["FastAPI (Python)"],
        "thumbnail": "api",
        "salary": 88000,
        "about_role": "Summit Ventures needs backend support for inventory, pricing, and fulfillment integrations.",
        "responsibilities": "Develop FastAPI services, write integration tests, connect warehouse and payment webhooks.",
        "requirements_education": "CS degree or proven backend portfolio.",
        "requirements_experience": "2+ years Python APIs in production.",
        "requirements_additional": "Idempotency, webhooks, and queue patterns.",
        "other_benefits": "Growth-stage equity, learning budget.",
        "company_description": "Summit Ventures modernizes online retail operations.",
    },
    # ── democlient4 — Blue Harbor Tech ──
    {
        "client_email": "democlient4@gmail.com",
        "title": "Python API Developer (Contract)",
        "skills": ["FastAPI (Python)", "Vanilla Javascript"],
        "thumbnail": "python",
        "salary": 85000,
        "negotiable": True,
        "about_role": "Blue Harbor Tech consults for enterprise clients. You will deliver a 6-month skills-assessment API MVP.",
        "responsibilities": "Build quiz APIs, admin endpoints, file uploads, and integration tests for client delivery.",
        "requirements_education": "Demonstrated backend portfolio.",
        "requirements_experience": "Solid Python and REST API experience.",
        "requirements_additional": "Client communication and documentation skills.",
        "other_benefits": "Contract-to-hire possible.",
        "company_description": "Blue Harbor Tech is a B2B software consultancy.",
    },
    {
        "client_email": "democlient4@gmail.com",
        "title": "Full-Stack Consultant — React & FastAPI",
        "skills": ["ReactJS", "FastAPI (Python)"],
        "thumbnail": "team",
        "salary": 102000,
        "about_role": "Blue Harbor Tech embeds engineers with clients. You will ship features end-to-end on a workforce analytics product.",
        "responsibilities": "React dashboards, FastAPI endpoints, PostgreSQL queries, and weekly client demos.",
        "requirements_education": "Equivalent experience accepted.",
        "requirements_experience": "3+ years full-stack delivery.",
        "requirements_additional": "Comfortable presenting work to stakeholders.",
        "other_benefits": "Consulting exposure, varied projects.",
        "company_description": "Blue Harbor Tech delivers software for enterprise teams.",
    },
    # ── democlient5 — Greenfield Studio ──
    {
        "client_email": "democlient5@gmail.com",
        "title": "Creative Web Developer — HTML/CSS/JS",
        "skills": ["HTML-CSS", "Vanilla Javascript"],
        "thumbnail": "design",
        "salary": 62000,
        "about_role": "Greenfield Studio builds interactive microsites for product launches. You will code bold, lightweight experiences.",
        "responsibilities": "Implement creative layouts, scroll interactions, and responsive breakpoints without heavy frameworks.",
        "requirements_education": "Portfolio-first hiring.",
        "requirements_experience": "2+ years front-of-frontend craft.",
        "requirements_additional": "Animation and storytelling sensibility.",
        "other_benefits": "Studio culture, project variety.",
        "company_description": "Greenfield Studio is a creative shop for web and mobile launches.",
    },
    {
        "client_email": "democlient5@gmail.com",
        "title": "React Prototype Engineer",
        "skills": ["ReactJS"],
        "thumbnail": "mobile",
        "salary": 75000,
        "negotiable": True,
        "about_role": "Greenfield Studio prototypes mobile-first apps for clients in 4–6 week sprints.",
        "responsibilities": "Rapid React prototyping, component reuse, and handoff documentation for production teams.",
        "requirements_education": "Any relevant background.",
        "requirements_experience": "1+ years shipping React prototypes or MVPs.",
        "requirements_additional": "Speed and clarity over perfection.",
        "other_benefits": "Flexible schedule, creative freedom.",
        "company_description": "Greenfield Studio turns ideas into shippable product demos.",
    },
    # ── democlient6 — Atlas Digital (fintech) ──
    {
        "client_email": "democlient6@gmail.com",
        "title": "C++ Performance Engineer",
        "skills": ["C++"],
        "thumbnail": "cpp",
        "salary": 120000,
        "about_role": "Atlas Digital optimizes low-latency trading and risk engines. You will profile and modernize core C++ services.",
        "responsibilities": "Profile hot paths, refactor modules, write benchmarks, and improve memory safety.",
        "requirements_education": "CS/EE degree preferred.",
        "requirements_experience": "4+ years modern C++ in production systems.",
        "requirements_additional": "CMake, sanitizers, multithreading.",
        "other_benefits": "Conference budget, competitive compensation.",
        "company_description": "Atlas Digital builds high-performance fintech infrastructure.",
    },
    {
        "client_email": "democlient6@gmail.com",
        "title": "Junior C++ / Systems Developer",
        "skills": ["C++"],
        "thumbnail": "fintech",
        "salary": 72000,
        "about_role": "Atlas Digital is growing its platform team maintaining pricing and reconciliation engines.",
        "responsibilities": "Fix bugs, add tests, assist with profiling, participate in code review.",
        "requirements_education": "CS degree or equivalent.",
        "requirements_experience": "Academic or personal C++ projects required.",
        "requirements_additional": "Interest in performance and data structures.",
        "other_benefits": "Mentorship, clear growth path.",
        "company_description": "Atlas Digital powers financial data pipelines.",
    },
    # ── democlient7 — Brightline Media (healthcare) ──
    {
        "client_email": "democlient7@gmail.com",
        "title": "React Healthcare Portal Developer",
        "skills": ["ReactJS", "HTML-CSS"],
        "thumbnail": "health",
        "salary": 94000,
        "about_role": "Brightline Media builds patient-facing portals. You will implement accessible React flows for scheduling and records.",
        "responsibilities": "Ship HIPAA-aware UI patterns, form validation, and integration with backend APIs.",
        "requirements_education": "Relevant degree or equivalent.",
        "requirements_experience": "2+ years React; healthcare or regulated industry a plus.",
        "requirements_additional": "Accessibility (WCAG) and security mindfulness.",
        "other_benefits": "Mission-driven culture, remote-friendly.",
        "company_description": "Brightline Media delivers healthcare technology with empathy.",
    },
    {
        "client_email": "democlient7@gmail.com",
        "title": "FastAPI Integrations Engineer",
        "skills": ["FastAPI (Python)"],
        "thumbnail": "api",
        "salary": 99000,
        "about_role": "Brightline Media connects EHR systems and patient apps. You will build reliable integration APIs.",
        "responsibilities": "Design FastAPI services, handle webhooks, write contract tests, monitor uptime.",
        "requirements_education": "BS or strong backend portfolio.",
        "requirements_experience": "3+ years Python API development.",
        "requirements_additional": "Experience with third-party API integrations.",
        "other_benefits": "Health benefits, learning stipend.",
        "company_description": "Brightline Media modernizes healthcare data exchange.",
    },
    # ── democlient8 — CoreStack Systems (marketing / AI) ──
    {
        "client_email": "democlient8@gmail.com",
        "title": "LLM Application Developer",
        "skills": ["LLM Basics"],
        "thumbnail": "llm",
        "salary": 110000,
        "about_role": "CoreStack Systems builds LLM-powered copy and campaign insights for marketing teams.",
        "responsibilities": "Prompt engineering, RAG pipelines, quality evaluation, and product iteration with stakeholders.",
        "requirements_education": "BS or bootcamp plus shipped AI projects.",
        "requirements_experience": "1+ years applying LLMs in products.",
        "requirements_additional": "Embeddings, chunking, cost/latency awareness.",
        "other_benefits": "Flexible PTO, learning budget.",
        "company_description": "CoreStack Systems applies AI to marketing operations.",
    },
    {
        "client_email": "democlient8@gmail.com",
        "title": "AI Automation Engineer (Part-time)",
        "skills": ["Agentic AI"],
        "thumbnail": "remote",
        "salary": 65000,
        "negotiable": True,
        "about_role": "CoreStack Systems automates research and reporting for campaign managers using agent workflows.",
        "responsibilities": "Build autonomous workflows, connect analytics APIs, document playbooks, monitor failures.",
        "requirements_education": "Portfolio of automation projects.",
        "requirements_experience": "Practical agent or workflow automation experience.",
        "requirements_additional": "Clear communication with non-technical teams.",
        "other_benefits": "20 hrs/week, fully remote.",
        "company_description": "CoreStack Systems is a marketing agency investing in AI ops.",
    },
    {
        "client_email": "democlient8@gmail.com",
        "title": "Agentic AI + LLM Platform Engineer",
        "skills": ["Agentic AI", "LLM Basics"],
        "thumbnail": "ai",
        "salary": 125000,
        "about_role": "CoreStack Systems is building an internal agent platform for multi-step marketing research tasks.",
        "responsibilities": "Design agent orchestration, tool integrations, eval suites, and production monitoring.",
        "requirements_education": "Applied AI or CS background.",
        "requirements_experience": "2+ years with LLMs and automation systems.",
        "requirements_additional": "Python proficiency and API design skills.",
        "other_benefits": "GPU credits, async team.",
        "company_description": "CoreStack Systems ships AI tooling for creative agencies.",
    },
    # ── democlient9 — Horizon Works (EdTech) ──
    {
        "client_email": "democlient9@gmail.com",
        "title": "EdTech React Course Platform Engineer",
        "skills": ["ReactJS", "Vanilla Javascript"],
        "thumbnail": "team",
        "salary": 86000,
        "about_role": "Horizon Works hosts professional courses and quizzes. You will improve the learner dashboard and quiz UX.",
        "responsibilities": "Build React learning flows, progress tracking UI, and responsive lesson layouts.",
        "requirements_education": "Equivalent experience accepted.",
        "requirements_experience": "2+ years React in consumer or EdTech products.",
        "requirements_additional": "Empathy for learner UX.",
        "other_benefits": "Free courses, remote work.",
        "company_description": "Horizon Works is an EdTech platform for professional upskilling.",
    },
    {
        "client_email": "democlient9@gmail.com",
        "title": "Quiz & Assessment API Engineer",
        "skills": ["FastAPI (Python)", "LLM Basics"],
        "thumbnail": "data",
        "salary": 92000,
        "about_role": "Horizon Works scales skills verification with quizzes and AI-generated study recommendations.",
        "responsibilities": "Extend quiz APIs, scoring logic, recommendation endpoints, and analytics pipelines.",
        "requirements_education": "CS or backend portfolio.",
        "requirements_experience": "Python API experience; assessment products a plus.",
        "requirements_additional": "Data modeling for learning outcomes.",
        "other_benefits": "Mission-aligned team, flexible hours.",
        "company_description": "Horizon Works connects courses to verifiable skills.",
    },
    # ── democlient10 — Lumen Agency ──
    {
        "client_email": "democlient10@gmail.com",
        "title": "Frontend Engineer — Design System",
        "skills": ["ReactJS", "HTML-CSS"],
        "thumbnail": "frontend",
        "salary": 88000,
        "about_role": "Lumen Agency is standardizing a design system across client deliverables and internal tools.",
        "responsibilities": "Build reusable React components, document patterns, enforce accessibility across projects.",
        "requirements_education": "Relevant degree or equivalent.",
        "requirements_experience": "2+ years on component libraries or design systems.",
        "requirements_additional": "Strong collaboration with designers.",
        "other_benefits": "Annual retreat, creative environment.",
        "company_description": "Lumen Agency is a digital marketing shop with engineering in-house.",
    },
    {
        "client_email": "democlient10@gmail.com",
        "title": "Marketing Site JavaScript Developer",
        "skills": ["Vanilla Javascript", "HTML-CSS"],
        "thumbnail": "javascript",
        "salary": 64000,
        "negotiable": True,
        "about_role": "Lumen Agency ships campaign landing pages under tight deadlines for brand clients.",
        "responsibilities": "Implement tracking, animations, form flows, and performance optimizations in vanilla JS.",
        "requirements_education": "Portfolio required.",
        "requirements_experience": "1+ years agency or freelance delivery.",
        "requirements_additional": "Comfortable with analytics pixels and tag managers.",
        "other_benefits": "Project variety, hybrid work.",
        "company_description": "Lumen Agency delivers high-impact digital campaigns.",
    },
]


async def resolve_client(session, email: str) -> tuple[User, ClientProfile]:
    result = await session.execute(
        select(User, ClientProfile)
        .join(ClientProfile, ClientProfile.user_id == User.id)
        .where(User.email == email, User.role == UserRole.client)
    )
    row = result.first()
    if row is None:
        raise RuntimeError(
            f"Client not found: {email}. Run scripts/seed_demo_users.py first."
        )
    return row[0], row[1]


async def load_skills_by_name(session) -> dict[str, Skill]:
    result = await session.execute(select(Skill).where(Skill.is_active.is_(True)))
    skills = result.scalars().all()
    by_name = {s.name: s for s in skills}
    if not by_name:
        raise RuntimeError("No skills in database. Run scripts/reseed_skills.py first.")
    return by_name


async def seed_jobs(session) -> dict[str, int]:
    skills_by_name = await load_skills_by_name(session)
    totals = {"created": 0, "skipped": 0}
    per_client: dict[str, int] = {}

    for spec in DEMO_JOBS:
        email = spec["client_email"]
        client, profile = await resolve_client(session, email)

        existing = await session.execute(
            select(Job.id).where(
                Job.client_id == client.id,
                Job.title == spec["title"],
            )
        )
        if existing.scalar_one_or_none() is not None:
            totals["skipped"] += 1
            continue

        missing = [name for name in spec["skills"] if name not in skills_by_name]
        if missing:
            raise RuntimeError(
                f"Skill(s) not in DB for '{spec['title']}' ({email}): {', '.join(missing)}"
            )

        salary = Decimal(str(spec["salary"]))
        negotiable = spec.get("negotiable", False)
        thumb_key = spec.get("thumbnail", "remote")

        job = Job(
            client_id=client.id,
            title=spec["title"],
            thumbnail_url=THUMBNAILS.get(thumb_key, THUMBNAILS["remote"]),
            description=spec["about_role"],
            about_role=spec["about_role"],
            responsibilities=spec["responsibilities"],
            requirements_education=spec["requirements_education"],
            requirements_experience=spec["requirements_experience"],
            requirements_additional=spec["requirements_additional"],
            other_benefits=spec["other_benefits"],
            company_name=profile.company_name,
            company_description=spec["company_description"],
            salary_amount=None if negotiable else salary,
            salary_negotiable=negotiable,
            deliverables=spec["responsibilities"],
            budget=salary,
            timeline=spec.get("timeline", "Full-time · Start within 30 days"),
            status=JobStatus.open,
        )
        session.add(job)
        await session.flush()

        for skill_name in spec["skills"]:
            session.add(
                JobRequiredSkill(
                    job_id=job.id,
                    skill_id=skills_by_name[skill_name].id,
                )
            )

        totals["created"] += 1
        per_client[email] = per_client.get(email, 0) + 1

    await session.commit()
    totals["per_client"] = per_client
    return totals


async def main() -> None:
    async with async_session_maker() as session:
        totals = await seed_jobs(session)

    print("Demo jobs seeded successfully.")
    print(f"  Created: {totals['created']}")
    print(f"  Skipped: {totals['skipped']} (duplicate title per client)")
    print(f"  Templates: {len(DEMO_JOBS)} across {len({j['client_email'] for j in DEMO_JOBS})} clients")
    print("  By client:")
    for email, count in sorted(totals.get("per_client", {}).items()):
        print(f"    {email}: +{count} new")


if __name__ == "__main__":
    asyncio.run(main())
