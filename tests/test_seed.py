from sqlalchemy import func, select

from api.models import Comment, Post, Tag, User, UserRole
from api.seed import COMMENTS, POSTS, USERS, seed


async def test_seed_inserts_starter_data(session):
    assert await seed(session) is True

    roles = set(await session.scalars(select(User.role)))
    assert roles == set(UserRole)
    assert await session.scalar(select(func.count()).select_from(User)) == len(USERS)
    assert await session.scalar(select(func.count()).select_from(Post)) == len(POSTS)
    assert await session.scalar(select(func.count()).select_from(Comment)) == len(
        COMMENTS
    )
    assert await session.scalar(select(func.count()).select_from(Tag)) > 0


async def test_seed_does_nothing_when_users_exist(session):
    await seed(session)
    assert await seed(session) is False
    assert await session.scalar(select(func.count()).select_from(User)) == len(USERS)


async def test_seeded_posts_are_served_by_the_api(session, client):
    await seed(session)
    response = await client.get("/posts")
    assert response.status_code == 200
    assert {post["title"] for post in response.json()} == {title for _, title, *_ in POSTS}
