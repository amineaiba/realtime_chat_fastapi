import os

# Point the app at the test services before anything imports the settings.
# Never fall back to DATABASE_URL: the tests wipe every table.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://chat:chat@localhost:55432/chat_test"
)
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:56379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")

from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from core.database import engine  # noqa: E402
from core.redis_manager import redis_client  # noqa: E402
from main import app  # noqa: E402
from routers.auth import limiter  # noqa: E402

PASSWORD = "Password1"
TABLES = "messages, room_members, rooms, refresh_tokens, profiles, users"


@dataclass
class LoggedInUser:
    id: str
    username: str
    email: str
    access_token: str
    client: TestClient

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    # Build the schema with the real migrations, so they are tested too.
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    limiter.enabled = False
    yield
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_state() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} CASCADE"))
    redis_client.flushdb()


def new_client() -> TestClient:
    # https, because the refresh cookie is Secure.
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def client() -> TestClient:
    return new_client()


@pytest.fixture
def make_user() -> Callable[[str], LoggedInUser]:
    """Register a user and log in with their own client (own cookie jar)."""

    def _make(username: str) -> LoggedInUser:
        client = new_client()
        email = f"{username}@example.com"
        res = client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": PASSWORD},
        )
        assert res.status_code == 200, res.text
        user_id = res.json()["id"]

        res = client.post("/auth/login", data={"username": email, "password": PASSWORD})
        assert res.status_code == 200, res.text
        return LoggedInUser(user_id, username, email, res.json()["access_token"], client)

    return _make
