import jwt
import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import _decode_supabase_jwt


async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "HTTP_401"


def test_decode_supabase_jwt_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")
    claims = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "a@example.com",
        "aud": "authenticated",
    }
    token = jwt.encode(claims, "test-secret", algorithm="HS256")

    payload = _decode_supabase_jwt(token)

    assert payload.sub == "11111111-1111-1111-1111-111111111111"
    assert payload.email == "a@example.com"


def test_decode_supabase_jwt_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")
    token = jwt.encode({"sub": "x", "aud": "authenticated"}, "wrong-secret", algorithm="HS256")

    with pytest.raises(HTTPException):
        _decode_supabase_jwt(token)
