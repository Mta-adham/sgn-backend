from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ContactIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    # Validated on the way in: this is a public, unauthenticated form, and an address
    # nobody can reply to makes the message useless.
    email: EmailStr
    company: str | None = None
    subject: str | None = None
    message: str | None = None


class ContactStatusUpdate(BaseModel):
    status: str


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str | None
    last_name: str | None
    email: str
    company: str | None
    subject: str | None
    message: str | None
    status: str
    created_at: datetime
