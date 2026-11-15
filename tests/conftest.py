import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.config import settings
from api.db import SessionLocal, engine
from api.main import app
from api.models import Base, User, UserRole


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
def clean_db() -> None:
    """Start every test with empty tables."""
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    """HTTP client that calls the app directly, without a running server."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session() -> Iterator[Session]:
    """A database session for setting up and checking data directly."""
    with SessionLocal() as db_session:
        yield db_session


@pytest.fixture
def make_user(session: Session) -> Callable[..., User]:
    """Insert a user straight into the database (there's no users endpoint)."""

    def _make_user(role: UserRole = UserRole.BLOGGER) -> User:
        username = f"user_{uuid.uuid4().hex[:8]}"
        user = User(
            username=username,
            email=f"{username}@example.com",
            display_name=username.title(),
            role=role,
        )
        session.add(user)
        session.commit()
        return user

    return _make_user


@pytest.fixture
def make_post(client: TestClient, make_user) -> Callable[..., dict]:
    """Create a post through the API and return its JSON."""

    def _make_post(**fields) -> dict:
        if "author_id" not in fields:
            fields["author_id"] = str(make_user().id)
        payload = {"title": "A title", "body": "Some body text", **fields}
        response = client.post("/posts", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_post
