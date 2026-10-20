import asyncio

import pytest

from core.socket_manager import sio
from sockets.handlers import handle_connect


@pytest.fixture
def fake_transport(monkeypatch):
    """Skip the real Socket.IO session store and emits; we only test the auth decision."""

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(sio, "save_session", noop)
    monkeypatch.setattr(sio, "emit", noop)


def connect(token: str | None) -> bool:
    auth = {"token": token} if token else None
    return asyncio.run(handle_connect("sid-1", {}, auth))


def test_connect_with_access_token_is_accepted(make_user, fake_transport):
    alice = make_user("alice")
    assert connect(alice.access_token) is True


def test_connect_without_token_is_refused(fake_transport):
    assert connect(None) is False


def test_connect_with_refresh_token_is_refused(make_user, fake_transport):
    alice = make_user("alice")
    assert connect(alice.client.cookies.get("refresh_token")) is False


def test_connect_after_logout_is_refused(make_user, fake_transport):
    alice = make_user("alice")
    alice.client.post("/auth/logout", headers=alice.headers)
    assert connect(alice.access_token) is False
