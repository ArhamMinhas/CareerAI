from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Verified claims from a Supabase-issued JWT — identity only, not authorization.
    App-level role lives on our own `users` row, never solely in the JWT (docs/SECURITY.md §2)."""

    sub: str
    email: str | None = None


@lru_cache
def _get_jwks_client() -> PyJWKClient:
    # PyJWKClient caches the fetched key set internally, so this only hits the network
    # again after the cache expires or a `kid` it hasn't seen shows up.
    return PyJWKClient(f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def _decode_supabase_jwt(token: str) -> TokenPayload:
    """Verifies a Supabase Auth JWT, supporting both signing methods Supabase projects can
    use — routed by the token's own `alg` header rather than a guess, since that's the one
    thing that's always correct for the token actually being verified:

    - **Legacy projects (HS256):** shared secret, `SUPABASE_JWT_SECRET`.
    - **Current projects (ES256/RS256):** asymmetric "JWT Signing Keys" — no shared secret
      exists; verified against the project's public JWKS endpoint instead, which requires
      only `SUPABASE_URL`.

    See docs/CONTRIBUTING.md §2.3 — this fork was flagged before either path was verified
    against a real project.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth is not configured (SUPABASE_JWT_SECRET is unset).",
                )
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            if not settings.supabase_url:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth is not configured (SUPABASE_URL is unset).",
                )
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Covers jwt.PyJWTError (bad signature/expiry) and PyJWKClient errors (network,
        # unknown kid, ...) alike — any failure here means "reject the token," never a 500
        # that could hint at internals.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenPayload(sub=payload["sub"], email=payload.get("email"))


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_supabase_jwt(credentials.credentials)


async def get_current_user(
    token: Annotated[TokenPayload, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolves the verified Supabase identity to our local `users` row, creating it on
    first sight (a user can be verified by Supabase before they've ever hit our API)."""
    result = await db.execute(select(User).where(User.id == token.sub))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=token.sub, email=token.email or "", role=Role.USER)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


def require_role(*roles: Role) -> Callable[[User], Awaitable[User]]:
    """FastAPI dependency factory for admin-only routes (docs/SECURITY.md §2), e.g.
    `Depends(require_role(Role.ADMIN))`."""

    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return _check
