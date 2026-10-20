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

from collections.abc import Awaitable, Callable, Iterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402

import anyio.from_thread  # noqa: E402
import pytest  # noqa: E402
import redis  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from core.database import engine  # noqa: E402
from main import app  # noqa: E402
from routers.auth import limiter  # noqa: E402

PASSWORD = "Password1"
TABLES = "messages, room_members, rooms, refresh_tokens, profiles, users"

# One event loop for the whole run, like one uvicorn worker in production.
# The async Redis pool is bound to the loop that opened its connections.
_portal: anyio.from_thread.BlockingPortal | None = None


def run_async(func: Callable[..., Awaitable], *args):
    """Run app coroutines (e.g. socket handlers) on the shared test loop."""
    assert _portal is not None
    return _portal.call(func, *args)


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

    global _portal
    with anyio.from_thread.start_blocking_portal() as portal:
        _portal = portal
        yield
        _portal = None

    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_state() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} CASCADE"))
    redis.from_url(os.environ["REDIS_URL"]).flushdb()


def new_client() -> TestClient:
    # https, because the refresh cookie is Secure.
    client = TestClient(app, base_url="https://testserver")
    client.portal = _portal
    return client


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
        return LoggedInUser(
            user_id, username, email, res.json()["access_token"], client
        )

    return _make
