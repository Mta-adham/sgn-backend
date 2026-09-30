from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConnectionRequestCreate(BaseModel):
    recipient_id: int
    # Short on purpose. This is a reason to connect, not a message thread, and a cap keeps
    # it that way without needing moderation.
    message: str | None = Field(default=None, max_length=500)


class ConnectionRespond(BaseModel):
    """Accept or decline. The recipient is the only one who may call this."""

    accept: bool


class ConnectionMemberOut(BaseModel):
    """The other party in a connection, as the viewer is allowed to see them.

    Email and phone are populated only once the request is accepted. Before that they are
    None, so a pending request reveals nothing the directory did not already show and
    cannot be used to collect contact details.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    company: str | None = None
    industries: list[str] = []
    categories: list[str] = []
    interests: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None


class ConnectionOut(BaseModel):
    id: int
    status: str
    message: str | None
    created_at: datetime
    responded_at: datetime | None
    # "incoming" if this member received it, "outgoing" if they sent it. The UI needs to
    # know which side it is showing, and deriving it here keeps that logic in one place.
    direction: str
    member: ConnectionMemberOut


class ConnectionReportCreate(BaseModel):
    reason: str
    details: str | None = Field(default=None, max_length=500)


class ConnectionReportOut(BaseModel):
    """A report as the admin queue sees it."""

    id: int
    reason: str
    details: str | None
    reported_message: str | None
    reviewed: bool
    created_at: datetime
    reporter_name: str
    reporter_email: str
    reported_name: str
    reported_email: str
    reported_member_id: int
    reported_member_active: bool
    # How many reports this member has against them in total. One report is a
    # disagreement; a pattern is the thing worth acting on.
    reports_against_member: int
