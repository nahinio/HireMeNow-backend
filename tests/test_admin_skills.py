import os

import pytest
from httpx import AsyncClient

from tests.test_integration import admin_login, create_skill_quiz

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Integration tests require TEST_DATABASE_URL",
)


@pytest.mark.asyncio
async def test_admin_delete_skill(client: AsyncClient):
    admin_token = await admin_login(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    skill_id, _, _, _, _ = await create_skill_quiz(client, admin_token, "DeleteMeSkill")

    response = await client.delete(f"/api/v1/admin/skills/{skill_id}", headers=headers)
    assert response.status_code == 204

    missing = await client.get(f"/api/v1/admin/skills/{skill_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_skill_not_found(client: AsyncClient):
    admin_token = await admin_login(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = await client.delete(
        "/api/v1/admin/skills/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404
