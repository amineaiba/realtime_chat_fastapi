import pytest
from conftest import run_async

from core.database import SessionLocal
from core.socket_manager import sio
from db_models.chat import Message
from sockets.handlers import handle_join_room, handle_send_message


@pytest.fixture
def deleted_group(make_user):
    alice, bob = make_user("alice"), make_user("bob")
    room = alice.client.post(
        "/chat/rooms/create",
        headers=alice.headers,
        json={"type": "group", "name": "Team", "member_ids": [bob.id]},
    ).json()
    alice.client.delete(f"/chat/rooms/{room['id']}", headers=alice.headers)
    return alice, bob, room["id"]


@pytest.fixture
def socket_as(monkeypatch):
    """Fake the Socket.IO transport: a fixed session user, and record emits."""
    emitted = []

    def _as(user_id: str):
        async def get_session(sid):
            return {"user_id": user_id}

        async def emit(event, data=None, **kwargs):
            emitted.append((event, data))

        async def enter_room(sid, room):
            emitted.append(("entered", room))

        monkeypatch.setattr(sio, "get_session", get_session)
        monkeypatch.setattr(sio, "emit", emit)
        monkeypatch.setattr(sio, "enter_room", enter_room)
        return emitted

    return _as


def test_deleted_group_cannot_be_renamed(deleted_group):
    alice, _, room_id = deleted_group
    res = alice.client.patch(
        f"/chat/rooms/{room_id}", headers=alice.headers, json={"name": "New"}
    )
    assert res.status_code == 404


def test_deleted_group_cannot_be_left(deleted_group):
    _, bob, room_id = deleted_group
    res = bob.client.delete(f"/chat/rooms/{room_id}/leave", headers=bob.headers)
    assert res.status_code == 404


def test_cannot_join_deleted_group_over_socket(deleted_group, socket_as):
    _, bob, room_id = deleted_group
    emitted = socket_as(bob.id)
    run_async(handle_join_room, "sid-1", {"room_id": room_id})
    assert [e for e, _ in emitted] == ["error"]


def test_cannot_send_to_deleted_group_over_socket(deleted_group, socket_as):
    _, bob, room_id = deleted_group
    emitted = socket_as(bob.id)
    run_async(handle_send_message, "sid-1", {"room_id": room_id, "content": "hi"})
    assert [e for e, _ in emitted] == ["error"]
    with SessionLocal() as db:
        assert db.query(Message).count() == 0
