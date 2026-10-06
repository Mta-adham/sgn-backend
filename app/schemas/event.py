from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class SpeakerIn(BaseModel):
    id: int | None = None
    name: str | None = None
    title: str | None = None
    bio: str | None = None
    image: str | None = None


class AgendaItemIn(BaseModel):
    id: int | None = None
    title: str | None = None
    speaker: str | None = None
    time: str | None = None


class PhotoIn(BaseModel):
    url: str
    caption: str | None = None
    order: int = 0


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    caption: str | None
    order: int


class EventIn(BaseModel):
    title: str
    description: str | None = None
    date: str | None = None
    time: str | None = None
    location: str | None = None
    event_type: str | None = None
    price: str | None = None
    image_url: str | None = None
    has_happened: bool = False
    published: bool = True
    speakers: list[SpeakerIn] = []
    agenda: list[AgendaItemIn] = []
    photos: list[PhotoIn] = []


class SpeakerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
    title: str | None
    bio: str | None
    image: str | None


class AgendaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str | None
    speaker: str | None
    time: str | None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    date: str | None
    time: str | None
    location: str | None
    event_type: str | None
    price: str | None
    image_url: str | None
    has_happened: bool
    published: bool
    created_at: datetime
    speakers: list[SpeakerOut] = []
    agenda: list[AgendaItemOut] = []
    photos: list[PhotoOut] = []


class RSVPRequest(BaseModel):
    event_id: int
    # Validated, because this address is the only thing tying an RSVP to a member account
    # (the member events endpoint matches on it). A typo here is an RSVP that silently
    # never shows up on anyone's dashboard.
    email: EmailStr
    names: str | None = None
    company: str | None = None
    price: str | None = None
    paymentIntentId: str | None = None


class RSVPOut(BaseModel):
    id: int
    names: str | None
    email: str
    company: str | None
    price: str | None
    rsvp: str
    paymentIntentId: str | None = None


class MemberEventOut(BaseModel):
    """One event the current member has registered for, with their own RSVP state.

    Kept separate from RSVPOut: that one is the admin's view of who is coming to an
    event, this one is a member's view of which events they are going to. The member
    never needs the other attendees' details, so they are not in this shape.
    """

    event_id: int
    title: str
    date: str | None
    time: str | None
    location: str | None
    event_type: str | None
    image_url: str | None
    has_happened: bool
    rsvp: str
    registered_at: datetime
    attended: bool


class PaymentIntentEventRequest(BaseModel):
    amount: float
    eventId: int
    event: str | None = None
    attendeeDetails: dict = {}


class PaymentIntentResponse(BaseModel):
    clientSecret: str
