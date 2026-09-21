import pytest

# (path, text the file must contain): guards against a page or script going missing, or being served wrongly.
FILES = [
    ("/", "/quiz.js"),
    ("/admin/", "/admin/admin.js"),
    ("/style.css", "--bg: #000"),
    ("/common.js", "function h("),
    ("/quiz.js", "/categories"),
    ("/admin/admin.js", "/admin/users"),
]


@pytest.mark.parametrize("path, marker", FILES)
def test_frontend_files_are_served(client, path, marker):
    res = client.get(path)

    assert res.status_code == 200
    assert marker in res.text


def test_api_routes_win_over_the_static_files(client):
    assert client.get("/api/categories").headers["content-type"].startswith("application/json")
    assert client.get("/docs").status_code == 200
