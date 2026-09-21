import os

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://quiz:quiz@localhost:5432/quiz_test")
ADMIN_USERNAME = "test-admin"
ADMIN_PASSWORD = "test-password"

# Settings are read when app.config is imported, so point the app at the test database *before* importing it.
os.environ.update(
    DATABASE_URL=TEST_DATABASE_URL,
    SECRET_KEY="test-secret-key-that-is-long-enough-for-hs256",
    ADMIN_USERNAME=ADMIN_USERNAME,
    ADMIN_PASSWORD=ADMIN_PASSWORD,
)


def _ensure_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    assert url.database and url.database.endswith("_test"), "refusing to run the tests against a non-test database"
    with psycopg.connect(
        host=url.host, port=url.port, user=url.username, password=url.password, dbname="postgres", autocommit=True
    ) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)).fetchone():
            conn.execute(f'CREATE DATABASE "{url.database}"')


_ensure_test_database()

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category, Question, Score, User  # noqa: E402

ADMIN_HASH = hash_password(ADMIN_PASSWORD)  # hashing is deliberately slow, so do it once


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(schema):
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def admin_user(db):
    user = User(username=ADMIN_USERNAME, password_hash=ADMIN_HASH)
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin_headers(client, admin_user):
    res = client.post("/api/admin/login", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def make_category(db):
    def make(name="Genel"):
        category = Category(name=name)
        db.add(category)
        db.commit()
        return category

    return make


@pytest.fixture
def make_question(db):
    def make(category, text="Soru?", options=("A", "B", "C", "D"), answer_index=1):
        question = Question(category_id=category.id, text=text, options=list(options), answer_index=answer_index)
        db.add(question)
        db.commit()
        return question

    return make


@pytest.fixture
def make_score(db):
    def make(category, player_name="Oyuncu", score=1, total=1):
        entry = Score(category_id=category.id, player_name=player_name, score=score, total=total)
        db.add(entry)
        db.commit()
        return entry

    return make
