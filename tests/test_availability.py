from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.schemas.freelancer import FreelancerProfileResponse
from app.utils.availability import (
    AVAILABLE_FOR_WORK,
    NOT_AVAILABLE_FOR_WORK,
    serialize_availability,
)


def test_serialize_availability_true():
    assert serialize_availability(True) == AVAILABLE_FOR_WORK
    assert serialize_availability(True) == "Available for Work"


def test_serialize_availability_false():
    assert serialize_availability(False) == NOT_AVAILABLE_FOR_WORK
    assert serialize_availability(False) == "Not Available for work"


def test_freelancer_profile_response_excludes_boolean():
    response = FreelancerProfileResponse(
        id=uuid4(),
        user_id=uuid4(),
        display_name="Dev",
        bio="",
        avg_rating=Decimal("0"),
        review_count=0,
        updated_at=datetime.now(timezone.utc),
        available_for_work=True,
    )
    payload = response.model_dump()
    assert "available_for_work" not in payload
    assert payload["availability_status"] == "Available for Work"

    response_unavailable = FreelancerProfileResponse(
        id=uuid4(),
        user_id=uuid4(),
        display_name="Dev",
        bio="",
        avg_rating=Decimal("0"),
        review_count=0,
        updated_at=datetime.now(timezone.utc),
        available_for_work=False,
    )
    assert (
        response_unavailable.model_dump()["availability_status"]
        == "Not Available for work"
    )
