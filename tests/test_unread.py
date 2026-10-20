from core.database import SessionLocal
from db_models.chat import Message


def send(room_id: str, sender) -> None:
    # Messages are created by the Socket.IO handler; insert directly for setup.
    with SessionLocal() as db:
        db.add(Message(room_id=room_id, sender_id=sender.id, content="hi"))
        db.commit()


def unread_in_list(user, room_id: str) -> int:
    rooms = user.client.get("/chat/rooms", headers=user.headers).json()
    return next(r["unread_count"] for r in rooms if r["id"] == room_id)


def global_unread(user) -> int:
    return user.client.get("/chat/unread-count", headers=user.headers).json()[
        "unread_count"
    ]


def test_own_messages_are_not_unread(make_user):
    alice, bob = make_user("alice"), make_user("bob")
    room = alice.client.post(
        "/chat/rooms/create",
        headers=alice.headers,
        json={"type": "dm", "member_ids": [bob.id]},
    ).json()

    send(room["id"], alice)
    send(room["id"], alice)
    send(room["id"], bob)

    assert unread_in_list(alice, room["id"]) == 1
    assert global_unread(alice) == 1
    assert unread_in_list(bob, room["id"]) == 2
    assert global_unread(bob) == 2


def test_mark_as_read_clears_unread(make_user):
    alice, bob = make_user("alice"), make_user("bob")
    room = alice.client.post(
        "/chat/rooms/create",
        headers=alice.headers,
        json={"type": "dm", "member_ids": [bob.id]},
    ).json()
    send(room["id"], alice)

    bob.client.put(f"/chat/rooms/{room['id']}/mark-as-read", headers=bob.headers)
    assert unread_in_list(bob, room["id"]) == 0
    assert global_unread(bob) == 0
