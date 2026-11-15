import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from api.db import get_session
from api.models import Post, Tag, User, UserRole
from api.schemas import PostCreate, PostRead, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])

SessionDep = Annotated[Session, Depends(get_session)]

# Posters can only comment and lurkers only read, so they can't author posts.
AUTHOR_ROLES = {UserRole.ADMIN, UserRole.BLOGGER}


def get_post_or_404(session: Session, post_id: uuid.UUID) -> Post:
    post = session.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Post {post_id} not found")
    return post


def get_or_create_tags(session: Session, names: list[str]) -> list[Tag]:
    """Return Tag rows for the given names, creating any that don't exist yet."""
    names = list(dict.fromkeys(names))  # drop duplicates, keep order
    if not names:
        return []
    session.execute(
        insert(Tag)
        .values([{"name": name} for name in names])
        .on_conflict_do_nothing(index_elements=[Tag.name])
    )
    return list(session.scalars(select(Tag).where(Tag.name.in_(names))))


@router.get("", response_model=list[PostRead])
def list_posts(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """List posts, newest first."""
    # selectinload fetches every post's tags in one extra query, instead of one per post.
    posts = session.scalars(
        select(Post)
        .options(selectinload(Post.tags))
        .order_by(Post.created_at.desc(), Post.id)
        .limit(limit)
        .offset(offset)
    )
    return posts.all()


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: uuid.UUID, session: SessionDep):
    return get_post_or_404(session, post_id)


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, session: SessionDep):
    author = session.get(User, payload.author_id)
    if author is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"User {payload.author_id} not found",
        )
    if author.role not in AUTHOR_ROLES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"User {author.id} has role '{author.role}' and can't write posts",
        )

    post = Post(
        author_id=author.id,
        title=payload.title,
        body=payload.body,
        tags=get_or_create_tags(session, payload.tags),
    )
    session.add(post)
    session.commit()
    session.refresh(post)  # load values the database set, like created_at
    return post


@router.patch("/{post_id}", response_model=PostRead)
def update_post(post_id: uuid.UUID, payload: PostUpdate, session: SessionDep):
    post = get_post_or_404(session, post_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return post

    if "tags" in changes:
        post.tags = get_or_create_tags(session, changes.pop("tags"))
    for field, value in changes.items():
        setattr(post, field, value)
    # Set explicitly so a tags-only change also counts as an update.
    post.updated_at = func.now()

    session.commit()
    session.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: uuid.UUID, session: SessionDep) -> None:
    """Delete a post. The database also removes its comments and tag links."""
    post = get_post_or_404(session, post_id)
    session.delete(post)
    session.commit()
