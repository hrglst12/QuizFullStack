import pytest


def submit(client, category, name="Ayşe", answers=()):
    return client.post(
        f"/api/categories/{category.id}/scores",
        json={"player_name": name, "answers": [{"question_id": q.id, "choice": c} for q, c in answers]},
    )


def test_submitted_score_is_graded_by_the_server(client, make_category, make_question):
    category = make_category()
    right = make_question(category, answer_index=1)
    wrong = make_question(category, answer_index=2)

    res = submit(client, category, name="  Ayşe  ", answers=[(right, 1), (wrong, 0)])

    assert res.status_code == 201
    body = res.json()
    assert (body["player_name"], body["score"], body["total"]) == ("Ayşe", 1, 2)
    assert body["created_at"]


def test_submitted_score_appears_on_the_leaderboard(client, make_category, make_question):
    category = make_category()
    question = make_question(category, answer_index=0)
    saved = submit(client, category, answers=[(question, 0)]).json()

    board = client.get(f"/api/categories/{category.id}/scores").json()

    assert [s["id"] for s in board] == [saved["id"]]


def test_score_for_unknown_category_is_404(client, make_category, make_question):
    category = make_category()
    question = make_question(category)

    res = client.post("/api/categories/999/scores", json={"player_name": "A", "answers": [{"question_id": question.id, "choice": 0}]})

    assert res.status_code == 404


@pytest.mark.parametrize("name", ["", "   ", "x" * 51])
def test_score_rejects_bad_player_names(client, make_category, make_question, name):
    category = make_category()
    question = make_question(category)

    assert submit(client, category, name=name, answers=[(question, 0)]).status_code == 422


def test_score_needs_at_least_one_answer(client, make_category):
    assert submit(client, make_category(), answers=[]).status_code == 422


def test_score_rejects_answering_the_same_question_twice(client, make_category, make_question):
    category = make_category()
    question = make_question(category, answer_index=0)

    assert submit(client, category, answers=[(question, 0), (question, 0)]).status_code == 422


def test_score_rejects_questions_from_another_category(client, make_category, make_question):
    mine, other = make_category("Benim"), make_category("Diğer")
    foreign = make_question(other)

    assert submit(client, mine, answers=[(foreign, 0)]).status_code == 422


def test_score_rejects_unknown_questions(client, make_category):
    class Ghost:
        id = 999

    assert submit(client, make_category(), answers=[(Ghost, 0)]).status_code == 422


def test_leaderboard_ranks_by_percentage_then_length_then_age(client, make_category, make_score):
    category = make_category()
    for name, score, total in [("yarım", 5, 10), ("üçte iki", 2, 3), ("tam-kısa", 1, 1), ("tam-uzun", 3, 3), ("ikinci-üçte-iki", 2, 3)]:
        make_score(category, name, score, total)

    board = client.get(f"/api/categories/{category.id}/scores").json()

    assert [s["player_name"] for s in board] == ["tam-uzun", "tam-kısa", "üçte iki", "ikinci-üçte-iki", "yarım"]


def test_leaderboard_is_limited_and_defaults_to_top_10(client, make_category, make_score):
    category = make_category()
    for n in range(12):
        make_score(category, f"Oyuncu {n}")

    assert len(client.get(f"/api/categories/{category.id}/scores").json()) == 10
    assert len(client.get(f"/api/categories/{category.id}/scores?limit=3").json()) == 3


@pytest.mark.parametrize("limit", [0, 101])
def test_leaderboard_limit_bounds(client, make_category, limit):
    category = make_category()

    assert client.get(f"/api/categories/{category.id}/scores?limit={limit}").status_code == 422


def test_leaderboard_only_shows_its_own_category(client, make_category, make_score):
    mine, other = make_category("Benim"), make_category("Diğer")
    make_score(mine, "benimki")
    make_score(other, "başkasının")

    board = client.get(f"/api/categories/{mine.id}/scores").json()

    assert [s["player_name"] for s in board] == ["benimki"]


def test_leaderboard_of_unknown_category_is_404(client):
    assert client.get("/api/categories/999/scores").status_code == 404
