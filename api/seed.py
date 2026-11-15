"""Fill an empty database with starter data. Run with `make seed`."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import SessionLocal
from api.models import Comment, Post, Tag, User, UserRole

USERS = [
    ("adam", "Adam Admin", UserRole.ADMIN),
    ("bella", "Bella Blogger", UserRole.BLOGGER),
    ("pete", "Pete Poster", UserRole.POSTER),
    ("lucy", "Lucy Lurker", UserRole.LURKER),
]

# (author username, title, body, tag names)
POSTS = [
    (
        "adam",
        "Welcome to the blog",
        "This is the first post. Say hello in the comments!",
        ["welcome"],
    ),
    (
        "bella",
        "Getting started with FastAPI",
        "FastAPI makes it quick to build typed JSON APIs in Python.",
        ["python", "fastapi"],
    ),
    (
        "bella",
        "Why we picked Postgres",
        "Postgres gives us constraints, cascades and solid tooling out of the box.",
        ["postgres"],
    ),
]

# (author username, index into POSTS, body)
COMMENTS = [
    ("pete", 0, "Glad to be here!"),
    ("bella", 0, "Thanks for having me as a blogger."),
    ("pete", 1, "Great intro, thanks!"),
]


def seed(session: Session) -> bool:
    """Insert the starter data. Returns False, changing nothing, if users already exist."""
    if session.scalar(select(func.count()).select_from(User)):
        return False

    users = {
        username: User(
            username=username,
            email=f"{username}@example.com",
            display_name=display_name,
            role=role,
        )
        for username, display_name, role in USERS
    }
    tag_names = sorted({name for *_, names in POSTS for name in names})
    tags = {name: Tag(name=name) for name in tag_names}
    session.add_all([*users.values(), *tags.values()])
    session.flush()  # assigns user ids

    posts = [
        Post(
            author_id=users[author].id,
            title=title,
            body=body,
            tags=[tags[name] for name in names],
        )
        for author, title, body, names in POSTS
    ]
    session.add_all(posts)
    session.flush()  # assigns post ids

    session.add_all(
        Comment(post_id=posts[post_index].id, user_id=users[author].id, body=body)
        for author, post_index, body in COMMENTS
    )
    session.commit()
    return True


def main() -> None:
    with SessionLocal() as session:
        seeded = seed(session)
    if seeded:
        print(
            f"Seeded {len(USERS)} users, {len(POSTS)} posts and {len(COMMENTS)} comments."
        )
    else:
        print("Database already has users; nothing seeded.")


if __name__ == "__main__":
    main()
