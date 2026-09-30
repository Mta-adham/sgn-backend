from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class MemberApplicationRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: str | None = None
    industry: str | None = None
    # The signup form asks for sectors as a multi-select. Without these fields the values
    # were accepted by the API and then silently dropped, so every application lost them.
    industries: list[str] = []
    categories: list[str] = []
    interests: str | None = None
    phone: str | None = None
    membershipTier: str
    paymentIntentId: str | None = None


class IndustryOut(BaseModel):
    """An industry option: label, sector group, and whether it is a Vision 2030 sector."""

    name: str
    group: str
    vision_2030: bool


class MemberAdminCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    company: str | None = None
    industry: str | None = None
    industries: list[str] = []
    interests: str | None = None
    phone: str | None = None
    membership_tier: str = "Basic Membership"
    categories: list[str] = []
    password: str


class MemberActiveUpdate(BaseModel):
    """Block (active=False) or unblock (active=True) a member."""

    active: bool


class MemberProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    industry: str | None = None
    interests: str | None = None
    phone: str | None = None
    bio: str | None = None
    linkedin: str | None = None
    twitter: str | None = None
    instagram: str | None = None
    website: str | None = None
    industries: list[str] | None = None
    categories: list[str] | None = None
    is_searchable: bool | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    company: str | None
    industry: str | None
    interests: str | None
    phone: str | None
    bio: str | None
    linkedin: str | None
    twitter: str | None
    instagram: str | None
    website: str | None
    membership_tier: str
    industries: list[str] = []
    categories: list[str] = []
    active: bool
    is_searchable: bool
    created_at: datetime
    blocked_at: datetime | None = None


class DirectoryMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    company: str | None
    industry: str | None
    interests: str | None
    categories: list[str] = []
    industries: list[str] = []
