import pytest


def create_dm(user, other):
    return user.client.post(
        "/chat/rooms/create",
        headers=user.headers,
        json={"type": "dm", "member_ids": [other.id]},
    )


def create_group(user, members, name="Team"):
    res = user.client.post(
        "/chat/rooms/create",
        headers=user.headers,
        json={"type": "group", "name": name, "member_ids": [m.id for m in members]},
    )
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def alice(make_user):
    return make_user("alice")


@pytest.fixture
def bob(make_user):
    return make_user("bob")


@pytest.fixture
def carol(make_user):
    return make_user("carol")


def test_dm_is_created_once_for_the_same_two_users(alice, bob):
    first = create_dm(alice, bob)
    assert first.status_code == 200
    assert first.json()["type"] == "dm"

    # Same pair, either direction, returns the same room.
    assert create_dm(alice, bob).json()["id"] == first.json()["id"]
    assert create_dm(bob, alice).json()["id"] == first.json()["id"]


def test_dm_with_yourself_is_refused(alice):
    assert create_dm(alice, alice).status_code == 400


def test_group_needs_a_name(alice, bob):
    res = alice.client.post(
        "/chat/rooms/create",
        headers=alice.headers,
        json={"type": "group", "member_ids": [bob.id]},
    )
    assert res.status_code == 400


def test_room_list_and_detail_for_members(alice, bob):
    room = create_group(alice, [bob])

    rooms = bob.client.get("/chat/rooms", headers=bob.headers).json()
    assert [r["id"] for r in rooms] == [room["id"]]

    detail = bob.client.get(f"/chat/rooms/{room['id']}", headers=bob.headers).json()
    assert {m["user"]["username"] for m in detail["members"]} == {"alice", "bob"}


def test_non_member_cannot_see_room_or_messages(alice, bob, carol):
    room = create_group(alice, [bob])
    assert (
        carol.client.get(f"/chat/rooms/{room['id']}", headers=carol.headers).status_code
        == 404
    )
    res = carol.client.get(f"/chat/rooms/{room['id']}/messages", headers=carol.headers)
    assert res.status_code == 404


def test_only_creator_can_update_group(alice, bob):
    room = create_group(alice, [bob])
    url = f"/chat/rooms/{room['id']}"

    assert (
        bob.client.patch(url, headers=bob.headers, json={"name": "Hacked"}).status_code
        == 403
    )

    res = alice.client.patch(url, headers=alice.headers, json={"name": "Renamed"})
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"


def test_only_creator_can_delete_group(alice, bob):
    room = create_group(alice, [bob])
    url = f"/chat/rooms/{room['id']}"

    assert bob.client.delete(url, headers=bob.headers).status_code == 403
    assert alice.client.delete(url, headers=alice.headers).status_code == 200

    # Deleted rooms are hidden from members.
    assert bob.client.get(url, headers=bob.headers).status_code == 404


def test_only_creator_can_remove_members(alice, bob, carol):
    room = create_group(alice, [bob, carol])
    url = f"/chat/rooms/{room['id']}/members/{carol.id}/delete"

    assert bob.client.delete(url, headers=bob.headers).status_code == 403
    assert alice.client.delete(url, headers=alice.headers).status_code == 200


def test_creator_can_add_member(alice, bob, carol):
    room = create_group(alice, [bob])
    res = alice.client.post(
        f"/chat/rooms/{room['id']}/members/add",
        headers=alice.headers,
        json={"user_to_add_id": carol.id},
    )
    assert res.status_code == 200
    assert (
        carol.client.get(f"/chat/rooms/{room['id']}", headers=carol.headers).status_code
        == 200
    )


def test_member_can_leave_but_creator_cannot(alice, bob):
    room = create_group(alice, [bob])
    url = f"/chat/rooms/{room['id']}/leave"

    assert alice.client.delete(url, headers=alice.headers).status_code == 400
    assert bob.client.delete(url, headers=bob.headers).status_code == 200
    assert bob.client.get("/chat/rooms", headers=bob.headers).json() == []


def test_user_search_excludes_self(alice, bob):
    res = alice.client.get("/users", headers=alice.headers, params={"q": "bo"})
    assert [u["username"] for u in res.json()] == ["bob"]
    res = alice.client.get("/users", headers=alice.headers, params={"q": "ali"})
    assert res.json() == []


def test_non_creator_cannot_add_member(alice, bob, carol):
    room = create_group(alice, [bob])
    res = bob.client.post(
        f"/chat/rooms/{room['id']}/members/add",
        headers=bob.headers,
        json={"user_to_add_id": carol.id},
    )
    assert res.status_code == 403


def test_adding_existing_member_is_a_conflict(alice, bob):
    room = create_group(alice, [bob])
    res = alice.client.post(
        f"/chat/rooms/{room['id']}/members/add",
        headers=alice.headers,
        json={"user_to_add_id": bob.id},
    )
    assert res.status_code == 409


def test_cannot_add_member_to_dm(alice, bob, carol):
    room = create_dm(alice, bob).json()
    res = alice.client.post(
        f"/chat/rooms/{room['id']}/members/add",
        headers=alice.headers,
        json={"user_to_add_id": carol.id},
    )
    assert res.status_code == 400


def test_room_list_includes_members_so_dms_can_show_the_partner(alice, bob):
    create_dm(alice, bob)
    rooms = alice.client.get("/chat/rooms", headers=alice.headers).json()
    assert {m["user"]["username"] for m in rooms[0]["members"]} == {"alice", "bob"}
