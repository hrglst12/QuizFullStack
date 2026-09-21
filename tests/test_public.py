import pytest


def test_categories_are_sorted_by_name_and_count_their_questions(client, make_category, make_question):
    b = make_category("B")
    a = make_category("A")
    make_question(b)
    make_question(b)

    assert client.get("/api/categories").json() == [
        {"id": a.id, "name": "A", "question_count": 0},
        {"id": b.id, "name": "B", "question_count": 2},
    ]


def test_questions_do_not_leak_the_correct_answer(client, make_category, make_question):
    category = make_category()
    make_question(category)

    (question,) = client.get(f"/api/categories/{category.id}/questions").json()

    assert set(question) == {"id", "category_id", "text", "options"}


def test_questions_only_come_from_the_requested_category(client, make_category, make_question):
    mine, other = make_category("Benim"), make_category("Diğer")
    wanted = make_question(mine)
    make_question(other)

    ids = [q["id"] for q in client.get(f"/api/categories/{mine.id}/questions").json()]

    assert ids == [wanted.id]


def test_questions_limit(client, make_category, make_question):
    category = make_category()
    for n in range(5):
        make_question(category, text=f"Soru {n}")

    assert len(client.get(f"/api/categories/{category.id}/questions").json()) == 5
    assert len(client.get(f"/api/categories/{category.id}/questions?limit=2").json()) == 2


@pytest.mark.parametrize("limit", [0, 51, -1])
def test_questions_limit_must_be_between_1_and_50(client, make_category, limit):
    category = make_category()

    assert client.get(f"/api/categories/{category.id}/questions?limit={limit}").status_code == 422


def test_questions_of_unknown_category_is_404(client):
    assert client.get("/api/categories/999/questions").status_code == 404


@pytest.mark.parametrize("choice, correct", [(2, True), (0, False), (99, False)])
def test_check_answer(client, make_category, make_question, choice, correct):
    question = make_question(make_category(), answer_index=2)

    res = client.post(f"/api/questions/{question.id}/answer", json={"choice": choice})

    assert res.status_code == 200
    assert res.json() == {"correct": correct, "answer_index": 2}


def test_check_answer_of_unknown_question_is_404(client):
    assert client.post("/api/questions/999/answer", json={"choice": 0}).status_code == 404


def test_check_answer_requires_a_choice(client, make_category, make_question):
    question = make_question(make_category())

    assert client.post(f"/api/questions/{question.id}/answer", json={}).status_code == 422
