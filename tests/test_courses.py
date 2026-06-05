import os

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Integration tests require TEST_DATABASE_URL",
)


async def admin_login(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def register_freelancer(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": "freelancer",
            "display_name": "Learner",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_publish_quiz_requires_at_least_one_course(client: AsyncClient):
    admin_token = await admin_login(client)
    skill = await client.post(
        "/api/v1/admin/skills",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Kubernetes"},
    )
    skill_id = skill.json()["id"]

    blocked = await client.post(
        "/api/v1/admin/quizzes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"skill_id": skill_id, "pass_threshold": 80, "published": True},
    )
    assert blocked.status_code == 422


@pytest.mark.asyncio
async def test_admin_course_crud_and_gallery_filters(client: AsyncClient):
    admin_token = await admin_login(client)
    skill = await client.post(
        "/api/v1/admin/skills",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "TypeScript"},
    )
    skill_id = skill.json()["id"]

    created = await client.post(
        "/api/v1/admin/courses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "skill_id": skill_id,
            "name": "TypeScript Fundamentals",
            "link": "https://example.com/ts",
            "thumbnail_url": "https://example.com/ts.png",
        },
    )
    assert created.status_code == 201
    course_id = created.json()["id"]

    admin_list = await client.get(
        "/api/v1/admin/courses",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"skill_id": skill_id, "q": "Fundamentals"},
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1

    gallery = await client.get(
        "/api/v1/courses",
        params={"skill_id": skill_id, "q": "Fundamentals"},
    )
    assert gallery.status_code == 200
    assert gallery.json()["total"] == 1
    assert gallery.json()["items"][0]["skill_name"] == "TypeScript"

    updated = await client.patch(
        f"/api/v1/admin/courses/{course_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Advanced TypeScript"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Advanced TypeScript"


@pytest.mark.asyncio
async def test_cannot_remove_last_active_course(client: AsyncClient):
    admin_token = await admin_login(client)
    skill = await client.post(
        "/api/v1/admin/skills",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Rust"},
    )
    skill_id = skill.json()["id"]
    course = await client.post(
        "/api/v1/admin/courses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "skill_id": skill_id,
            "name": "Rust Starter",
            "link": "https://example.com/rust",
        },
    )
    course_id = course.json()["id"]

    blocked = await client.delete(
        f"/api/v1/admin/courses/{course_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert blocked.status_code == 422


@pytest.mark.asyncio
async def test_quiz_fail_recommends_skill_courses(client: AsyncClient):
    admin_token = await admin_login(client)
    skill = await client.post(
        "/api/v1/admin/skills",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "GraphQL"},
    )
    skill_id = skill.json()["id"]
    await client.post(
        "/api/v1/admin/courses",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "skill_id": skill_id,
            "name": "GraphQL in Practice",
            "link": "https://example.com/graphql",
            "thumbnail_url": "https://example.com/gql.png",
        },
    )
    quiz = await client.post(
        "/api/v1/admin/quizzes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"skill_id": skill_id, "pass_threshold": 80, "published": True},
    )
    quiz_id = quiz.json()["id"]
    question = await client.post(
        f"/api/v1/admin/quizzes/{quiz_id}/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"body": "Pick wrong", "position": 1},
    )
    question_id = question.json()["id"]
    wrong = await client.post(
        f"/api/v1/admin/questions/{question_id}/options",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"body": "Wrong", "is_correct": False},
    )
    await client.post(
        f"/api/v1/admin/questions/{question_id}/options",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"body": "Right", "is_correct": True},
    )

    freelancer_token = await register_freelancer(client, "learner@example.com")
    attempt = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": question_id, "selected_option_id": wrong.json()["id"]}],
    )
    assert attempt.status_code == 200
    data = attempt.json()
    assert data["result"] == "fail"
    assert len(data["recommended_courses"]) == 1
    assert data["recommended_courses"][0]["name"] == "GraphQL in Practice"
    assert data["recommended_courses"][0]["link"] == "https://example.com/graphql"
