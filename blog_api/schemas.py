import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

# Tag names are stripped and lowercased, so "Python " and "python" are the same tag.
TagName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=50),
]
Title = Annotated[str, Field(min_length=1, max_length=200)]
Body = Annotated[str, Field(min_length=1)]


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author_id: uuid.UUID
    title: Title
    body: Body
    tags: list[TagName] = []


class PostUpdate(BaseModel):
    """PATCH body. Only the fields sent are changed; `tags` replaces the whole set."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    body: Body | None = None
    tags: list[TagName] | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "PostUpdate":
        # None means "not sent". Sending null explicitly is an error.
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    body: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def tag_names(cls, tags: list[Any]) -> list[str]:
        # The ORM gives Tag objects; the API returns their names.
        return [getattr(tag, "name", tag) for tag in tags]
