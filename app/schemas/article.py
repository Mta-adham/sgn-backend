from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ArticleIn(BaseModel):
    title: str
    excerpt: str | None = None
    content: str | None = None
    author: str | None = None
    category: str | None = None
    image_url: str | None = None
    published: bool = False


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    excerpt: str | None
    content: str | None
    author: str | None
    category: str | None
    image_url: str | None
    published: bool
    created_at: datetime
