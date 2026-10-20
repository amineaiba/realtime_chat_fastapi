from conftest import PASSWORD, new_client


def refresh_with(token: str) -> int:
    """Call /auth/refresh from a fresh client that holds only this token."""
    client = new_client()
    client.cookies.set("refresh_token", token)
    return client.post("/auth/refresh").status_code


def test_register_and_login(client):
    res = client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": PASSWORD},
    )
    assert res.status_code == 200
    assert res.json()["username"] == "alice"

    res = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": PASSWORD}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert "refresh_token" in res.cookies


def test_register_duplicate_user_is_refused(client, make_user):
    make_user("alice")
    res = client.post(
        "/auth/register",
        json={"username": "alice", "email": "other@example.com", "password": PASSWORD},
    )
    assert res.status_code == 400


def test_register_weak_password_is_refused(client):
    res = client.post(
        "/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "password"},
    )
    assert res.status_code == 422


def test_login_wrong_password(client, make_user):
    make_user("alice")
    res = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "Wrong1234"}
    )
    assert res.status_code == 401


def test_me_returns_current_user(make_user):
    alice = make_user("alice")
    res = alice.client.get("/auth/me", headers=alice.headers)
    assert res.status_code == 200
    assert res.json()["id"] == alice.id


def test_refresh_rotates_and_old_token_is_refused(make_user):
    alice = make_user("alice")
    old_refresh = alice.client.cookies.get("refresh_token")

    res = alice.client.post("/auth/refresh")
    assert res.status_code == 200
    new_refresh = alice.client.cookies.get("refresh_token")
    assert new_refresh != old_refresh

    # Refresh tokens are single-use. The new one still works.
    assert refresh_with(old_refresh) == 401
    assert refresh_with(new_refresh) == 200


def test_logout_blocks_access_token_and_refresh(make_user):
    alice = make_user("alice")
    refresh = alice.client.cookies.get("refresh_token")

    res = alice.client.post("/auth/logout", headers=alice.headers)
    assert res.status_code == 204

    assert alice.client.get("/auth/me", headers=alice.headers).status_code == 401

    assert refresh_with(refresh) == 401


def test_change_password_logs_out_every_session(make_user, client):
    alice = make_user("alice")
    refresh = alice.client.cookies.get("refresh_token")
    res = alice.client.post(
        "/auth/change-password",
        headers=alice.headers,
        json={"old_password": PASSWORD, "new_password": "NewPassword2"},
    )
    assert res.status_code == 200

    assert refresh_with(refresh) == 401

    res = client.post(
        "/auth/login", data={"username": alice.email, "password": "NewPassword2"}
    )
    assert res.status_code == 200


def test_protected_route_rejects_bad_token(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert res.status_code == 401
