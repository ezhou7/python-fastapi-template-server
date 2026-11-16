import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# How constraints and indexes get named, so every database has the same predictable
# names (a later migration needs the name to change or drop one).
# %(column_0_N_name)s joins all the columns: idx_posts_author_id_created_at.
NAMING_CONVENTION = {
    PrimaryKeyConstraint: "pk_%(table_name)s",
    ForeignKeyConstraint: "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    UniqueConstraint: "uniq_%(table_name)s_%(column_0_N_name)s",
    CheckConstraint: "ck_%(table_name)s_%(constraint_name)s",
    Index: "idx_%(table_name)s_%(column_0_N_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    BLOGGER = "blogger"
    POSTER = "poster"  # can write comments, not posts
    LURKER = "lurker"  # reads only


class IdTimestampMixin:
    """UUID primary key plus created_at / updated_at."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        sort_order=-1,  # first column
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), sort_order=1
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        sort_order=1,
    )


class User(IdTimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    # Stored as VARCHAR + CHECK constraint (not a Postgres ENUM type), so roles
    # are easy to change later. values_callable stores "blogger", not "BLOGGER".
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        default=UserRole.LURKER,
        server_default=UserRole.LURKER.value,
    )


class Tag(IdTimestampMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True)


class Post(IdTimestampMixin, Base):
    __tablename__ = "posts"

    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)

    # The post's tags, found through the tag_post table (TagPost below).
    # Assigning post.tags adds and removes tag_post rows automatically.
    # Loaded on first access. passive_deletes: when a post is deleted, the
    # database removes its tag_post rows (ON DELETE CASCADE), not the ORM.
    tags: Mapped[list[Tag]] = relationship(
        secondary="tag_post", order_by=Tag.name, passive_deletes=True
    )


class TagPost(Base):
    """Which post has which tag: one row per link.

    No id or timestamps of its own; the (post_id, tag_id) pair is the primary key,
    so a tag can't be linked to the same post twice. Rows go away when either the
    post or the tag is deleted.
    """

    __tablename__ = "tag_post"

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    # Its own index for "posts with this tag". "Tags of this post" already uses
    # the primary key's index, which starts with post_id.
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Comment(IdTimestampMixin, Base):
    __tablename__ = "comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
