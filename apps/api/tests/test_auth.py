import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from httpx import AsyncClient
from jwt import PyJWK

from app.core.config import settings
from app.core.security import _decode_supabase_jwt


class _FakeJWKClient:
    """Stands in for `PyJWKClient` in tests — real JWKS verification is exercised against
    a real Supabase project instead (docs/CONTRIBUTING.md §2.3), so this only needs to
    return a known key without a network call."""

    def __init__(self, signing_key: PyJWK) -> None:
        self._signing_key = signing_key

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        return self._signing_key


def _pyjwk_for(public_key: ec.EllipticCurvePublicKey) -> PyJWK:
    algorithm = jwt.algorithms.ECAlgorithm(jwt.algorithms.ECAlgorithm.SHA256)
    return PyJWK.from_json(algorithm.to_jwk(public_key))


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


def test_decode_supabase_jwt_accepts_valid_es256_token_via_jwks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Current Supabase projects (asymmetric 'JWT Signing Keys') have no shared secret —
    this exercises that path, mirroring what a live end-to-end test against a real project
    confirmed (docs/CONTRIBUTING.md §2.3): the token's own `alg` header routes to JWKS-based
    verification with no `SUPABASE_JWT_SECRET` involved at all."""
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")

    private_key = ec.generate_private_key(ec.SECP256R1())
    claims = {
        "sub": "22222222-2222-2222-2222-222222222222",
        "email": "b@example.com",
        "aud": "authenticated",
    }
    token = jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": "test-kid"})

    fake_client = _FakeJWKClient(_pyjwk_for(private_key.public_key()))
    monkeypatch.setattr("app.core.security._get_jwks_client", lambda: fake_client)

    payload = _decode_supabase_jwt(token)

    assert payload.sub == "22222222-2222-2222-2222-222222222222"
    assert payload.email == "b@example.com"


def test_decode_supabase_jwt_rejects_es256_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")

    signing_key = ec.generate_private_key(ec.SECP256R1())
    other_key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated"},
        other_key,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )

    fake_client = _FakeJWKClient(_pyjwk_for(signing_key.public_key()))
    monkeypatch.setattr("app.core.security._get_jwks_client", lambda: fake_client)

    with pytest.raises(HTTPException):
        _decode_supabase_jwt(token)
