import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal, engine
from app.core.security import get_current_user
from app.main import app
from app.models.user import Role, User


@pytest.fixture(autouse=True)
async def _fresh_engine_per_test() -> None:
    """pytest-asyncio gives each test function its own event loop, but `engine` (app/core/
    db.py) is a module-level singleton whose connection pool binds to whichever loop was
    running when a connection was first opened. Without this, a later test's loop inherits
    pooled connections tied to an already-closed loop from an earlier test, surfacing as
    "attached to a different loop" / "Event loop is closed" during teardown — not a bug in
    the test itself. Disposing before each test forces fresh connections under the loop
    that's actually running now."""
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authed_client() -> AsyncGenerator[AsyncClient]:
    """A client authenticated as a throwaway user, real-inserted into `users` (profile/
    education/etc. all FK to a row that has to actually exist) and deleted afterward —
    these tests run against the real dev Postgres, not a per-test transaction, so cleanup
    matters. `get_current_user` is overridden rather than minting a real Supabase JWT: the
    JWT verification path itself is already covered by tests/test_auth.py."""
    test_user = User(id=uuid.uuid4(), email=f"test-{uuid.uuid4()}@example.com", role=Role.USER)

    async with AsyncSessionLocal() as session:
        session.add(test_user)
        await session.commit()

    async def _override_user() -> User:
        return test_user

    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    del app.dependency_overrides[get_current_user]
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.id == test_user.id))
        await session.commit()
