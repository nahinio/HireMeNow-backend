import pytest
from httpx import AsyncClient

from tests.test_integration import create_skill_quiz


@pytest.mark.asyncio
async def test_list_skills_includes_published_quiz(client: AsyncClient):
    admin_login = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    admin_token = admin_login.json()["access_token"]
    skill_id, quiz_id, _, _, _ = await create_skill_quiz(
        client, admin_token, "PublicSkillList"
    )

    response = await client.get("/api/v1/skills", params={"q": "PublicSkillList"})
    assert response.status_code == 200
    payload = response.json()
    match = next(item for item in payload["items"] if item["id"] == skill_id)
    assert match["quiz"]["quiz_id"] == quiz_id
    assert match["quiz"]["pass_threshold"] == 80
    assert match["quiz"]["question_count"] == 1


@pytest.mark.asyncio
async def test_get_quiz_hides_correct_answers(client: AsyncClient):
    admin_login = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    admin_token = admin_login.json()["access_token"]
    _, quiz_id, question_id, wrong_id, correct_id = await create_skill_quiz(
        client, admin_token, "PublicQuizDetail"
    )

    response = await client.get(f"/api/v1/quizzes/{quiz_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_name"] == "PublicQuizDetail"
    assert len(payload["questions"]) == 1
    question = payload["questions"][0]
    assert question["id"] == question_id
    option_ids = {option["id"] for option in question["options"]}
    assert option_ids == {wrong_id, correct_id}
    assert all("is_correct" not in option for option in question["options"])


@pytest.mark.asyncio
async def test_get_unpublished_quiz_returns_404(client: AsyncClient):
    admin_login = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@hiremenow.com", "password": "password"},
    )
    admin_token = admin_login.json()["access_token"]
    skill = await client.post(
        "/api/v1/admin/skills",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "UnpublishedSkillOnly"},
    )
    skill_id = skill.json()["id"]
    quiz = await client.post(
        "/api/v1/admin/quizzes",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"skill_id": skill_id, "pass_threshold": 80, "published": False},
    )
    quiz_id = quiz.json()["id"]

    response = await client.get(f"/api/v1/quizzes/{quiz_id}")
    assert response.status_code == 404
