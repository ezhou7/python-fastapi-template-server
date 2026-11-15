from sqlalchemy import func, select

from api.models import Comment, Post, Tag, User, UserRole
from api.seed import COMMENTS, POSTS, USERS, seed


def test_seed_inserts_starter_data(session):
    assert seed(session) is True

    roles = set(session.scalars(select(User.role)))
    assert roles == set(UserRole)
    assert session.scalar(select(func.count()).select_from(User)) == len(USERS)
    assert session.scalar(select(func.count()).select_from(Post)) == len(POSTS)
    assert session.scalar(select(func.count()).select_from(Comment)) == len(
        COMMENTS
    )
    assert session.scalar(select(func.count()).select_from(Tag)) > 0


def test_seed_does_nothing_when_users_exist(session):
    seed(session)
    assert seed(session) is False
    assert session.scalar(select(func.count()).select_from(User)) == len(USERS)


def test_seeded_posts_are_served_by_the_api(session, client):
    seed(session)
    response = client.get("/posts")
    assert response.status_code == 200
    assert {post["title"] for post in response.json()} == {title for _, title, *_ in POSTS}
