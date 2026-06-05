import os

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Integration tests require TEST_DATABASE_URL",
)


async def register_user(client: AsyncClient, email: str, role: str, **extra):
    payload = {"email": email, "password": "password123", "role": role, **extra}
    return await client.post("/api/v1/auth/register", json=payload)


async def login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def create_skill_quiz(
    client: AsyncClient, admin_token: str, skill_name: str
) -> tuple[str, str, str, str]:
    skill = await client.post(
        "/api/v1/admin/skills",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": skill_name},
    )
    skill_id = skill.json()["id"]
    quiz = await client.post(
        "/api/v1/admin/quizzes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"skill_id": skill_id, "pass_threshold": 80, "published": True},
    )
    quiz_id = quiz.json()["id"]
    question = await client.post(
        f"/api/v1/admin/quizzes/{quiz_id}/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"body": f"{skill_name} question", "position": 1},
    )
    question_id = question.json()["id"]
    await client.post(
        f"/api/v1/admin/questions/{question_id}/options",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"body": "Wrong", "is_correct": False},
    )
    correct = await client.post(
        f"/api/v1/admin/questions/{question_id}/options",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"body": "Right", "is_correct": True},
    )
    return skill_id, quiz_id, question_id, correct.json()["id"]


@pytest.mark.asyncio
async def test_register_login_profile_flow(client: AsyncClient):
    assert (await register_user(
        client, "freelancer@example.com", "freelancer", display_name="Alice"
    )).status_code == 201

    token = await login(client, "freelancer@example.com")
    response = await client.patch(
        "/api/v1/freelancer/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"available_for_work": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["availability_status"] == "Not Available for work"
    assert "available_for_work" not in data


@pytest.mark.asyncio
async def test_multi_skill_gate_and_duplicate_application(client: AsyncClient):
    await register_user(client, "admin@example.com", "admin")
    admin_token = await login(client, "admin@example.com")

    skill_a_id, quiz_a_id, q_a_id, opt_a_id = await create_skill_quiz(
        client, admin_token, "Python"
    )
    skill_b_id, quiz_b_id, q_b_id, opt_b_id = await create_skill_quiz(
        client, admin_token, "FastAPI"
    )

    await register_user(
        client, "freelancer2@example.com", "freelancer", display_name="Bob"
    )
    freelancer_token = await login(client, "freelancer2@example.com")

    await client.post(
        f"/api/v1/quizzes/{quiz_a_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": q_a_id, "selected_option_id": opt_a_id}],
    )

    await register_user(
        client, "client@example.com", "client", company_name="Acme"
    )
    client_token = await login(client, "client@example.com")

    job = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "title": "Backend Dev",
            "description": "Build API",
            "deliverables": "API",
            "budget": "1000",
            "timeline": "2 weeks",
            "required_skill_ids": [skill_a_id, skill_b_id],
        },
    )
    job_id = job.json()["id"]

    missing = await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    assert missing.status_code == 403
    assert "FastAPI" in str(missing.json()["detail"])

    await client.post(
        f"/api/v1/quizzes/{quiz_b_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": q_b_id, "selected_option_id": opt_b_id}],
    )

    success = await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    assert success.status_code == 201

    duplicate = await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_freelancer_cannot_initiate_conversation(client: AsyncClient):
    await register_user(client, "admin3@example.com", "admin")
    admin_token = await login(client, "admin3@example.com")
    skill_id, quiz_id, question_id, option_id = await create_skill_quiz(
        client, admin_token, "React"
    )

    await register_user(
        client, "freelancer3@example.com", "freelancer", display_name="Carol"
    )
    freelancer_token = await login(client, "freelancer3@example.com")
    await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": question_id, "selected_option_id": option_id}],
    )

    await register_user(
        client, "client3@example.com", "client", company_name="Beta"
    )
    client_token = await login(client, "client3@example.com")
    job = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "title": "Frontend",
            "description": "UI",
            "deliverables": "UI",
            "budget": "500",
            "timeline": "1 week",
            "required_skill_ids": [skill_id],
        },
    )
    job_id = job.json()["id"]
    await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    freelancer_user_id = me.json()["id"]

    blocked = await client.post(
        "/api/v1/conversations/initiate",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json={"job_id": job_id, "freelancer_id": freelancer_user_id},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_conversation_lock_after_completion_signal(client: AsyncClient):
    await register_user(client, "admin4@example.com", "admin")
    admin_token = await login(client, "admin4@example.com")
    skill_id, quiz_id, question_id, option_id = await create_skill_quiz(
        client, admin_token, "Docker"
    )

    await register_user(
        client, "freelancer4@example.com", "freelancer", display_name="Dan"
    )
    freelancer_token = await login(client, "freelancer4@example.com")
    await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": question_id, "selected_option_id": option_id}],
    )

    await register_user(
        client, "client4@example.com", "client", company_name="Gamma"
    )
    client_token = await login(client, "client4@example.com")
    job = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "title": "DevOps",
            "description": "Containers",
            "deliverables": "Setup",
            "budget": "800",
            "timeline": "3 weeks",
            "required_skill_ids": [skill_id],
        },
    )
    job_id = job.json()["id"]
    await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    freelancer_user_id = me.json()["id"]

    conv = await client.post(
        "/api/v1/conversations/initiate",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"job_id": job_id, "freelancer_id": freelancer_user_id},
    )
    conversation_id = conv.json()["id"]

    ok = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"body": "Hello"},
    )
    assert ok.status_code == 201

    await client.post(
        f"/api/v1/jobs/{job_id}/complete",
        headers={"Authorization": f"Bearer {client_token}"},
    )

    locked = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json={"body": "Reply"},
    )
    assert locked.status_code == 403


@pytest.mark.asyncio
async def test_double_blind_review_gate(client: AsyncClient):
    await register_user(client, "admin5@example.com", "admin")
    admin_token = await login(client, "admin5@example.com")
    skill_id, quiz_id, question_id, option_id = await create_skill_quiz(
        client, admin_token, "SQL"
    )

    await register_user(
        client, "freelancer5@example.com", "freelancer", display_name="Eve"
    )
    freelancer_token = await login(client, "freelancer5@example.com")
    await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": question_id, "selected_option_id": option_id}],
    )

    await register_user(
        client, "client5@example.com", "client", company_name="Delta"
    )
    client_token = await login(client, "client5@example.com")
    job = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "title": "DB Work",
            "description": "Schema",
            "deliverables": "Schema",
            "budget": "600",
            "timeline": "2 weeks",
            "required_skill_ids": [skill_id],
        },
    )
    job_id = job.json()["id"]
    await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )

    await client.post(
        f"/api/v1/jobs/{job_id}/complete",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    await client.post(
        f"/api/v1/jobs/{job_id}/complete",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )

    client_review = await client.post(
        f"/api/v1/jobs/{job_id}/review",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"rating": 5, "body": "Excellent work, would hire again."},
    )
    assert client_review.status_code == 201
    assert client_review.json()["is_published"] is False

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    freelancer_user_id = me.json()["id"]
    public = await client.get(f"/api/v1/users/{freelancer_user_id}/reviews")
    assert public.status_code == 200
    assert public.json() == []

    await client.post(
        f"/api/v1/jobs/{job_id}/review",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json={"rating": 4, "body": "Good client, clear requirements."},
    )

    public_after = await client.get(f"/api/v1/users/{freelancer_user_id}/reviews")
    assert len(public_after.json()) == 1


@pytest.mark.asyncio
async def test_review_validation(client: AsyncClient):
    await register_user(client, "admin6@example.com", "admin")
    admin_token = await login(client, "admin6@example.com")
    skill_id, quiz_id, question_id, option_id = await create_skill_quiz(
        client, admin_token, "Go"
    )

    await register_user(
        client, "freelancer6@example.com", "freelancer", display_name="Frank"
    )
    freelancer_token = await login(client, "freelancer6@example.com")
    await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempt",
        headers={"Authorization": f"Bearer {freelancer_token}"},
        json=[{"question_id": question_id, "selected_option_id": option_id}],
    )

    await register_user(
        client, "client6@example.com", "client", company_name="Epsilon"
    )
    client_token = await login(client, "client6@example.com")
    job = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {client_token}"},
        json={
            "title": "Go API",
            "description": "Service",
            "deliverables": "Service",
            "budget": "700",
            "timeline": "2 weeks",
            "required_skill_ids": [skill_id],
        },
    )
    job_id = job.json()["id"]
    await client.post(
        f"/api/v1/jobs/{job_id}/apply",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )
    await client.post(
        f"/api/v1/jobs/{job_id}/complete",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    await client.post(
        f"/api/v1/jobs/{job_id}/complete",
        headers={"Authorization": f"Bearer {freelancer_token}"},
    )

    short_body = await client.post(
        f"/api/v1/jobs/{job_id}/review",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"rating": 5, "body": "Too short"},
    )
    assert short_body.status_code == 422

    bad_rating = await client.post(
        f"/api/v1/jobs/{job_id}/review",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"rating": 0, "body": "Valid length review body here."},
    )
    assert bad_rating.status_code == 422
