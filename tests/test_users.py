import pytest
from sqlalchemy import select

from app.auth import ensure_admin, passwords
from app.config import settings
from app.models import User
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def login(client, username, password):
    return client.post("/api/admin/login", data={"username": username, "password": password})


def bearer(res):
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create(client, headers, username="ayse", password="gizli-sifre-1"):
    return client.post("/api/admin/users", json={"username": username, "password": password}, headers=headers)


# --- create / read ----------------------------------------------------------------------------------------------------


def test_create_user(client, admin_headers):
    res = create(client, admin_headers, username="  ayse  ")

    assert res.status_code == 201
    assert res.json() == {"id": res.json()["id"], "username": "ayse", "created_at": res.json()["created_at"]}
    assert res.json()["created_at"]


def test_the_password_is_stored_hashed_and_never_returned(client, admin_headers, db):
    res = create(client, admin_headers, password="gizli-sifre-1")

    assert "password" not in res.json() and "password_hash" not in res.json()
    stored = db.get(User, res.json()["id"]).password_hash
    assert stored != "gizli-sifre-1" and stored.startswith("$argon2")
    assert passwords.verify("gizli-sifre-1", stored)


def test_list_and_get_users_never_expose_hashes(client, admin_headers, admin_user):
    create(client, admin_headers)

    users = client.get("/api/admin/users", headers=admin_headers).json()
    one = client.get(f"/api/admin/users/{users[0]['id']}", headers=admin_headers).json()

    assert [u["username"] for u in users] == [ADMIN_USERNAME, "ayse"]
    assert all(set(u) == {"id", "username", "created_at"} for u in [*users, one])


def test_get_unknown_user_is_404(client, admin_headers):
    assert client.get("/api/admin/users/999", headers=admin_headers).status_code == 404


def test_duplicate_username_is_a_conflict(client, admin_headers):
    create(client, admin_headers, username="ayse")

    assert create(client, admin_headers, username="ayse").status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"username": "", "password": "gizli-sifre-1"},
        {"username": "   ", "password": "gizli-sifre-1"},
        {"username": "x" * 51, "password": "gizli-sifre-1"},
        {"username": "ayse", "password": "kisa"},
        {"username": "ayse", "password": "x" * 129},
        {"username": "ayse"},
        {"password": "gizli-sifre-1"},
    ],
    ids=["empty-name", "blank-name", "long-name", "short-password", "long-password", "no-password", "no-username"],
)
def test_create_user_validates_input(client, admin_headers, body):
    assert client.post("/api/admin/users", json=body, headers=admin_headers).status_code == 422


# --- logging in as a created user -------------------------------------------------------------------------------------


def test_a_created_user_can_log_in_and_use_the_admin_api(client, admin_headers):
    create(client, admin_headers, username="ayse", password="gizli-sifre-1")

    res = login(client, "ayse", "gizli-sifre-1")

    assert res.status_code == 200
    assert client.get("/api/admin/questions", headers=bearer(res)).status_code == 200
    assert login(client, "ayse", "yanlis-sifre-1").status_code == 401


# --- update -----------------------------------------------------------------------------------------------------------


def test_update_username_keeps_the_password_and_existing_tokens(client, admin_headers):
    user_id = create(client, admin_headers, username="ayse", password="gizli-sifre-1").json()["id"]
    token = bearer(login(client, "ayse", "gizli-sifre-1"))

    res = client.put(f"/api/admin/users/{user_id}", json={"username": "fatma"}, headers=admin_headers)

    assert res.status_code == 200 and res.json()["username"] == "fatma"
    assert login(client, "fatma", "gizli-sifre-1").status_code == 200
    assert login(client, "ayse", "gizli-sifre-1").status_code == 401
    assert client.get("/api/admin/questions", headers=token).status_code == 200


def test_update_password_replaces_the_old_one(client, admin_headers):
    user_id = create(client, admin_headers, username="ayse", password="eski-sifre-1").json()["id"]

    res = client.put(
        f"/api/admin/users/{user_id}", json={"username": "ayse", "password": "yeni-sifre-1"}, headers=admin_headers
    )

    assert res.status_code == 200
    assert login(client, "ayse", "yeni-sifre-1").status_code == 200
    assert login(client, "ayse", "eski-sifre-1").status_code == 401


def test_update_rejects_a_short_password(client, admin_headers):
    user_id = create(client, admin_headers).json()["id"]

    res = client.put(f"/api/admin/users/{user_id}", json={"username": "ayse", "password": "kisa"}, headers=admin_headers)

    assert res.status_code == 422


def test_rename_to_an_existing_username_is_a_conflict(client, admin_headers):
    create(client, admin_headers, username="ayse")
    other = create(client, admin_headers, username="fatma").json()["id"]

    res = client.put(f"/api/admin/users/{other}", json={"username": "ayse"}, headers=admin_headers)

    assert res.status_code == 409


def test_update_unknown_user_is_404(client, admin_headers):
    assert client.put("/api/admin/users/999", json={"username": "x"}, headers=admin_headers).status_code == 404


# --- delete -----------------------------------------------------------------------------------------------------------


def test_delete_user_and_their_token_stops_working_immediately(client, admin_headers):
    user_id = create(client, admin_headers, username="ayse", password="gizli-sifre-1").json()["id"]
    token = bearer(login(client, "ayse", "gizli-sifre-1"))
    assert client.get("/api/admin/questions", headers=token).status_code == 200

    assert client.delete(f"/api/admin/users/{user_id}", headers=admin_headers).status_code == 204

    assert client.get("/api/admin/questions", headers=token).status_code == 401
    assert login(client, "ayse", "gizli-sifre-1").status_code == 401
    assert client.delete(f"/api/admin/users/{user_id}", headers=admin_headers).status_code == 404


def test_the_last_user_cannot_be_deleted(client, admin_headers, admin_user):
    res = client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)

    assert res.status_code == 409
    assert login(client, ADMIN_USERNAME, ADMIN_PASSWORD).status_code == 200


def test_a_user_can_delete_themselves_while_others_remain(client, admin_headers, admin_user):
    create(client, admin_headers)

    assert client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers).status_code == 204
    assert login(client, "ayse", "gizli-sifre-1").status_code == 200


# --- first admin comes from .env --------------------------------------------------------------------------------------


def test_ensure_admin_creates_the_first_user_from_settings(client, db):
    ensure_admin()

    assert [u.username for u in db.scalars(select(User))] == [settings.admin_username]
    assert login(client, ADMIN_USERNAME, ADMIN_PASSWORD).status_code == 200


def test_ensure_admin_does_nothing_once_a_user_exists(client, admin_headers, db):
    other = create(client, admin_headers, username="ayse").json()["id"]
    client.delete(f"/api/admin/users/{db.scalar(select(User.id).where(User.username == ADMIN_USERNAME))}", headers=admin_headers)

    ensure_admin()

    assert [u.id for u in db.scalars(select(User))] == [other]


def test_ensure_admin_does_not_overwrite_a_changed_password(client, admin_headers, admin_user):
    client.put(
        f"/api/admin/users/{admin_user.id}",
        json={"username": ADMIN_USERNAME, "password": "degisti-sifre-1"},
        headers=admin_headers,
    )

    ensure_admin()

    assert login(client, ADMIN_USERNAME, "degisti-sifre-1").status_code == 200
    assert login(client, ADMIN_USERNAME, ADMIN_PASSWORD).status_code == 401
