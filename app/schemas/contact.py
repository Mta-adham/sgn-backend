from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContactIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str
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
