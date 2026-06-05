import uuid

import pytest
from fastapi import HTTPException

from app.models.enums import UserRole
from app.models.user import User
from app.services.reports import create_user_report


class FakeSession:
    def __init__(self, reported_user: User | None, pending_report=None):
        self.reported_user = reported_user
        self.pending_report = pending_report
        self.added = []

    async def execute(self, statement):
        class Result:
            def __init__(self, outer):
                self.outer = outer

            def scalar_one_or_none(self):
                sql = str(statement)
                if "users" in sql and "user_reports" not in sql:
                    return self.outer.reported_user
                if "user_reports" in sql:
                    return self.outer.pending_report
                return None

        return Result(self)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None


def _user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        password_hash="hash",
        role=role,
    )


@pytest.mark.asyncio
async def test_create_report_rejects_same_role():
    reporter = _user(UserRole.freelancer)
    reported = _user(UserRole.freelancer)
    session = FakeSession(reported_user=reported)

    with pytest.raises(HTTPException) as exc:
        await create_user_report(
            session,
            reporter=reporter,
            reported_user_id=reported.id,
            description="Bad actor",
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_create_report_allows_opposite_roles():
    reporter = _user(UserRole.client)
    reported = _user(UserRole.freelancer)
    session = FakeSession(reported_user=reported)

    report = await create_user_report(
        session,
        reporter=reporter,
        reported_user_id=reported.id,
        description="Bad actor",
    )
    assert report.reporter_id == reporter.id
    assert report.reported_user_id == reported.id
