import uuid

import pytest
from sqlalchemy import func, select

from api.models import Comment, Tag, UserRole, tag_post

MISSING_ID = "00000000-0000-0000-0000-000000000000"


def count(session, table) -> int:
    return session.scalar(select(func.count()).select_from(table))


# --- POST /posts ---------------------------------------------------------------


def test_create_post(client, make_user):
    author = make_user()
    response = client.post(
        "/posts",
        json={"author_id": str(author.id), "title": "Hello", "body": "World"},
    )

    assert response.status_code == 201
    post = response.json()
    assert post["author_id"] == str(author.id)
    assert post["title"] == "Hello"
    assert post["body"] == "World"
    assert post["tags"] == []
    uuid.UUID(post["id"])
    assert post["created_at"] == post["updated_at"]


def test_create_post_normalizes_and_dedupes_tags(make_post):
    post = make_post(tags=["Python", " fastapi ", "python"])
    assert post["tags"] == ["fastapi", "python"]


def test_create_post_reuses_existing_tags(make_post, session):
    make_post(tags=["python"])
    make_post(tags=["python", "sql"])
    assert count(session, Tag) == 2


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.BLOGGER])
def test_create_post_allowed_roles(make_post, make_user, role):
    author = make_user(role)
    post = make_post(author_id=str(author.id))
    assert post["author_id"] == str(author.id)


@pytest.mark.parametrize("role", [UserRole.POSTER, UserRole.LURKER])
def test_create_post_rejects_roles_that_cannot_blog(client, make_user, role):
    author = make_user(role)
    response = client.post(
        "/posts", json={"author_id": str(author.id), "title": "x", "body": "y"}
    )
    assert response.status_code == 422
    assert f"role '{role}'" in response.json()["detail"]


def test_create_post_rejects_unknown_author(client):
    response = client.post(
        "/posts", json={"author_id": MISSING_ID, "title": "x", "body": "y"}
    )
    assert response.status_code == 422
    assert "not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "bad_fields",
    [
        {"title": ""},
        {"body": ""},
        {"title": "x" * 201},
        {"tags": [" "]},
        {"unexpected": "field"},
    ],
)
def test_create_post_validates_body(client, make_user, bad_fields):
    author = make_user()
    payload = {"author_id": str(author.id), "title": "x", "body": "y", **bad_fields}
    response = client.post("/posts", json=payload)
    assert response.status_code == 422


# --- GET /posts and /posts/{id} ---------------------------------------------------


def test_get_post(client, make_post):
    created = make_post(tags=["python"])
    response = client.get(f"/posts/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_post_not_found(client):
    response = client.get(f"/posts/{MISSING_ID}")
    assert response.status_code == 404


def test_get_post_invalid_id(client):
    response = client.get("/posts/not-a-uuid")
    assert response.status_code == 422


def test_list_posts_newest_first_with_paging(client, make_post):
    first = make_post(title="first")
    second = make_post(title="second")
    third = make_post(title="third")

    response = client.get("/posts")
    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [third["id"], second["id"], first["id"]]

    response = client.get("/posts", params={"limit": 1, "offset": 1})
    assert [p["id"] for p in response.json()] == [second["id"]]


def test_list_posts_empty(client):
    response = client.get("/posts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_posts_rejects_bad_paging(client, params):
    response = client.get("/posts", params=params)
    assert response.status_code == 422


# --- PATCH /posts/{id} ----------------------------------------------------------


def test_patch_changes_only_given_fields(client, make_post):
    created = make_post(title="Old", body="Keep me", tags=["python"])
    response = client.patch(f"/posts/{created['id']}", json={"title": "New"})

    assert response.status_code == 200
    post = response.json()
    assert post["title"] == "New"
    assert post["body"] == "Keep me"
    assert post["tags"] == ["python"]
    assert post["created_at"] == created["created_at"]
    assert post["updated_at"] > created["updated_at"]


def test_patch_replaces_tags(client, make_post, session):
    created = make_post(tags=["python", "sql"])
    response = client.patch(
        f"/posts/{created['id']}", json={"tags": ["Rust", "python"]}
    )

    assert response.status_code == 200
    post = response.json()
    assert post["tags"] == ["python", "rust"]
    assert post["updated_at"] > created["updated_at"]
    assert count(session, tag_post) == 2
    assert count(session, Tag) == 3  # "sql" stays in tags, unlinked


def test_patch_empty_tags_removes_all(client, make_post):
    created = make_post(tags=["python"])
    response = client.patch(f"/posts/{created['id']}", json={"tags": []})
    assert response.json()["tags"] == []


def test_patch_empty_body_changes_nothing(client, make_post):
    created = make_post()
    response = client.patch(f"/posts/{created['id']}", json={})
    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize(
    "bad_fields",
    [{"title": None}, {"body": None}, {"tags": None}, {"title": ""}, {"author_id": MISSING_ID}],
)
def test_patch_validates_body(client, make_post, bad_fields):
    created = make_post()
    response = client.patch(f"/posts/{created['id']}", json=bad_fields)
    assert response.status_code == 422


def test_patch_not_found(client):
    response = client.patch(f"/posts/{MISSING_ID}", json={"title": "x"})
    assert response.status_code == 404


# --- DELETE /posts/{id} ---------------------------------------------------------


def test_delete_post_cascades(client, make_post, make_user, session):
    created = make_post(tags=["python"])
    commenter = make_user(UserRole.POSTER)
    session.add(Comment(post_id=created["id"], user_id=commenter.id, body="Nice"))
    session.commit()

    response = client.delete(f"/posts/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    assert client.get(f"/posts/{created['id']}").status_code == 404
    assert count(session, Comment) == 0
    assert count(session, tag_post) == 0
    assert count(session, Tag) == 1  # tags themselves are kept


def test_delete_post_not_found(client):
    response = client.delete(f"/posts/{MISSING_ID}")
    assert response.status_code == 404
