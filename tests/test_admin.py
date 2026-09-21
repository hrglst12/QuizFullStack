from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import Question, Score
from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME

PROTECTED = [
    ("get", "/api/admin/questions"),
    ("post", "/api/admin/categories"),
    ("put", "/api/admin/categories/1"),
    ("delete", "/api/admin/categories/1"),
    ("post", "/api/admin/questions"),
    ("put", "/api/admin/questions/1"),
    ("delete", "/api/admin/questions/1"),
    ("get", "/api/admin/users"),
    ("post", "/api/admin/users"),
    ("get", "/api/admin/users/1"),
    ("put", "/api/admin/users/1"),
    ("delete", "/api/admin/users/1"),
]


def question_body(category, **overrides):
    return {"category_id": category.id, "text": "Soru?", "options": ["A", "B", "C"], "answer_index": 1} | overrides


# --- authentication -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("method, path", PROTECTED)
def test_admin_endpoints_require_a_token(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.parametrize("method, path", PROTECTED)
def test_admin_endpoints_reject_garbage_tokens(client, method, path):
    assert getattr(client, method)(path, headers={"Authorization": "Bearer nonsense"}).status_code == 401


def token_for(sub, key=None, expires_in=timedelta(hours=1)):
    return jwt.encode({"sub": sub, "exp": datetime.now(timezone.utc) + expires_in}, key or settings.secret_key, "HS256")


def test_a_hand_made_token_is_accepted_when_valid(client, admin_user):
    """Guards the other token tests: they fail only for the one thing they change."""
    headers = {"Authorization": f"Bearer {token_for(str(admin_user.id))}"}

    assert client.get("/api/admin/questions", headers=headers).status_code == 200


def test_swagger_offers_both_login_and_pasting_a_token(client):
    spec = client.get("/openapi.json").json()

    assert set(spec["components"]["securitySchemes"]) == {"OAuth2PasswordBearer", "HTTPBearer"}
    schemes = {name for requirement in spec["paths"]["/api/admin/questions"]["get"]["security"] for name in requirement}
    assert schemes == {"OAuth2PasswordBearer", "HTTPBearer"}
    assert "security" not in spec["paths"]["/api/categories"]["get"]  # public endpoints stay unlocked


def test_admin_endpoints_reject_a_non_bearer_authorization_header(client, admin_user):
    headers = {"Authorization": f"Basic {token_for(str(admin_user.id))}"}

    assert client.get("/api/admin/questions", headers=headers).status_code == 401


def test_admin_endpoints_reject_expired_tokens(client, admin_user):
    expired = token_for(str(admin_user.id), expires_in=timedelta(minutes=-1))

    assert client.get("/api/admin/questions", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_admin_endpoints_reject_tokens_signed_with_another_key(client, admin_user):
    forged = token_for(str(admin_user.id), key="x" * 40)

    assert client.get("/api/admin/questions", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


@pytest.mark.parametrize("sub", ["999", "admin", ""], ids=["unknown-user-id", "old-style-username", "empty"])
def test_admin_endpoints_reject_tokens_for_nobody(client, admin_user, sub):
    assert client.get("/api/admin/questions", headers={"Authorization": f"Bearer {token_for(sub)}"}).status_code == 401


def test_login_returns_a_working_token(client, admin_user):
    res = client.post("/api/admin/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})

    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get("/api/admin/questions", headers=headers).status_code == 200


@pytest.mark.parametrize("username, password", [(ADMIN_USERNAME, "wrong"), ("wrong", ADMIN_PASSWORD)])
def test_login_rejects_bad_credentials(client, admin_user, username, password):
    assert client.post("/api/admin/login", data={"username": username, "password": password}).status_code == 401


def test_login_rejects_empty_credentials(client):
    assert client.post("/api/admin/login", data={"username": "", "password": ""}).status_code == 422


# --- categories -----------------------------------------------------------------------------------------------------


def test_create_category(client, admin_headers):
    res = client.post("/api/admin/categories", json={"name": "  Tarih  "}, headers=admin_headers)

    assert res.status_code == 201
    assert res.json() == {"id": res.json()["id"], "name": "Tarih", "question_count": 0}


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_create_category_validates_the_name(client, admin_headers, name):
    assert client.post("/api/admin/categories", json={"name": name}, headers=admin_headers).status_code == 422


def test_duplicate_category_name_is_a_conflict(client, admin_headers, make_category):
    make_category("Tarih")

    assert client.post("/api/admin/categories", json={"name": "Tarih"}, headers=admin_headers).status_code == 409


def test_update_category(client, admin_headers, make_category):
    category = make_category("Eski")

    res = client.put(f"/api/admin/categories/{category.id}", json={"name": "Yeni"}, headers=admin_headers)

    assert res.status_code == 200
    assert res.json()["name"] == "Yeni"


def test_rename_to_an_existing_name_is_a_conflict(client, admin_headers, make_category):
    make_category("Var")
    other = make_category("Başka")

    res = client.put(f"/api/admin/categories/{other.id}", json={"name": "Var"}, headers=admin_headers)

    assert res.status_code == 409


def test_update_unknown_category_is_404(client, admin_headers):
    assert client.put("/api/admin/categories/999", json={"name": "X"}, headers=admin_headers).status_code == 404


def test_delete_category(client, admin_headers, make_category):
    category = make_category()

    assert client.delete(f"/api/admin/categories/{category.id}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/admin/categories/{category.id}", headers=admin_headers).status_code == 404


def test_deleting_a_category_deletes_its_questions_and_scores(
    client, admin_headers, db, make_category, make_question, make_score
):
    doomed, kept = make_category("Silinecek"), make_category("Kalacak")
    make_question(doomed)
    make_score(doomed)
    survivor = make_question(kept)

    client.delete(f"/api/admin/categories/{doomed.id}", headers=admin_headers)

    assert [q.id for q in db.scalars(select(Question))] == [survivor.id]
    assert db.scalars(select(Score)).all() == []


# --- questions ------------------------------------------------------------------------------------------------------


def test_create_question(client, admin_headers, make_category):
    category = make_category()

    res = client.post("/api/admin/questions", json=question_body(category), headers=admin_headers)

    assert res.status_code == 201
    assert res.json() | {"id": None} == question_body(category) | {"id": None}
    assert client.get("/api/categories").json()[0]["question_count"] == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"answer_index": 3},  # points past the 3 options
        {"answer_index": -1},
        {"options": ["yalnız"]},  # fewer than 2
        {"options": list("ABCDEFG")},  # more than 6
        {"options": ["A", "  "]},  # blank option
        {"text": "   "},
    ],
    ids=["answer-out-of-range", "answer-negative", "one-option", "seven-options", "blank-option", "blank-text"],
)
def test_create_question_validates_input(client, admin_headers, make_category, overrides):
    body = question_body(make_category(), **overrides)

    assert client.post("/api/admin/questions", json=body, headers=admin_headers).status_code == 422


def test_create_question_in_unknown_category_is_404(client, admin_headers, make_category):
    body = question_body(make_category(), category_id=999)

    assert client.post("/api/admin/questions", json=body, headers=admin_headers).status_code == 404


def test_list_questions_newest_first_and_filterable(client, admin_headers, make_category, make_question):
    a, b = make_category("A"), make_category("B")
    first, second, third = make_question(a), make_question(b), make_question(a)

    everything = client.get("/api/admin/questions", headers=admin_headers).json()
    only_a = client.get(f"/api/admin/questions?category_id={a.id}", headers=admin_headers).json()

    assert [q["id"] for q in everything] == [third.id, second.id, first.id]
    assert [q["id"] for q in only_a] == [third.id, first.id]


def test_admin_list_includes_the_correct_answer(client, admin_headers, make_category, make_question):
    make_question(make_category(), answer_index=2)

    (question,) = client.get("/api/admin/questions", headers=admin_headers).json()

    assert question["answer_index"] == 2


def test_update_question_can_move_it_to_another_category(client, admin_headers, make_category, make_question):
    old, new = make_category("Eski"), make_category("Yeni")
    question = make_question(old)

    res = client.put(
        f"/api/admin/questions/{question.id}",
        json=question_body(new, text="Güncel?", answer_index=0),
        headers=admin_headers,
    )

    assert res.status_code == 200
    assert (res.json()["category_id"], res.json()["text"], res.json()["answer_index"]) == (new.id, "Güncel?", 0)


def test_update_unknown_question_is_404(client, admin_headers, make_category):
    res = client.put("/api/admin/questions/999", json=question_body(make_category()), headers=admin_headers)

    assert res.status_code == 404


def test_delete_question(client, admin_headers, make_category, make_question):
    question = make_question(make_category())

    assert client.delete(f"/api/admin/questions/{question.id}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/admin/questions/{question.id}", headers=admin_headers).status_code == 404
