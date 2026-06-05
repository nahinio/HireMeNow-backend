from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

def test_bcrypt_hash_and_verify_round_trip():
    hashed = hash_password("secret-password")
    assert hashed != "secret-password"
    assert verify_password("secret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_create_and_decode():
    token = create_access_token(
        {"sub": "user-123", "role": "freelancer"},
        expires_delta=timedelta(minutes=30),
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "freelancer"
    assert "exp" in payload


def test_jwt_expiry_detection():
    token = create_access_token(
        {"sub": "user-123", "role": "freelancer"},
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_jwt_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not-a-valid-token")
    assert exc_info.value.status_code == 401
