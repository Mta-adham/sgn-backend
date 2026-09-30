from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Legacy free-text industry, superseded by `industries`. Kept so no existing value is
    # lost; new writes go to the array column.
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Industries this member operates in. Multi-select, validated against INDUSTRIES in
    # app/core/industries.py.
    industries: Mapped[list[str]] = mapped_column(
        ARRAY(String(120)), nullable=False, server_default="{}", default=list
    )
    interests: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    twitter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # What kind of member this is. Multi-select: someone can be both an investor and a
    # company owner. Valid values are defined by MEMBER_CATEGORIES in app/core/categories.py.
    categories: Mapped[list[str]] = mapped_column(
        ARRAY(String(60)), nullable=False, server_default="{}", default=list
    )

    membership_tier: Mapped[str] = mapped_column(String(60), default="Basic Membership")
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # False until an admin reviews and activates a public membership application
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    # When the member was last blocked (i.e. the date they left the network).
    # Set when active flips to False, cleared when they are unblocked again.
    blocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Opt-in only: a member is never listed in the directory unless they explicitly turn this on
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
