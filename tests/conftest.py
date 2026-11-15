import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db import SessionLocal, engine
from api.main import app
from api.models import Base, User, UserRole

MakeUser = Callable[..., Awaitable[User]]


def pytest_configure(config: pytest.Config) -> None:
    # Every test truncates all tables, so never run against a non-test database.
    database = make_url(settings.database_url).database or ""
    if not database.endswith("_test"):
        pytest.exit(
            f"DATABASE_URL points at '{database}', not a *_test database. "
            "Run the tests with `make test`.",
            returncode=1,
        )


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    """Start every test with empty tables."""
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    yield
    # Each test runs on its own event loop; pooled connections can't be reused
    # across loops, so close them at the end of every test.
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP client that calls the app directly, without a running server."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """A database session for setting up and checking data directly."""
    async with SessionLocal() as db_session:
        yield db_session


@pytest.fixture
def make_user(session: AsyncSession) -> MakeUser:
    """Insert a user straight into the database (there's no users endpoint)."""

    async def _make_user(role: UserRole = UserRole.BLOGGER) -> User:
        username = f"user_{uuid.uuid4().hex[:8]}"
        user = User(
            username=username,
            email=f"{username}@example.com",
            display_name=username.title(),
            role=role,
        )
        session.add(user)
        await session.commit()
        return user

    return _make_user


@pytest.fixture
def make_post(client: AsyncClient, make_user: MakeUser):
    """Create a post through the API and return its JSON."""

    async def _make_post(**fields) -> dict:
        if "author_id" not in fields:
            fields["author_id"] = str((await make_user()).id)
        payload = {"title": "A title", "body": "Some body text", **fields}
        response = await client.post("/posts", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_post
