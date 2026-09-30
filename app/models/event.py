from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[str | None] = mapped_column(String(60), nullable=True)
    time: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    price: Mapped[str | None] = mapped_column(String(60), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    has_happened: Mapped[bool] = mapped_column(Boolean, default=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    speakers: Mapped[list["EventSpeaker"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="EventSpeaker.id"
    )
    agenda: Mapped[list["EventAgendaItem"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="EventAgendaItem.order"
    )
    rsvps: Mapped[list["RSVP"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventSpeaker(Base):
    __tablename__ = "event_speakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    event: Mapped[Event] = relationship(back_populates="speakers")


class EventAgendaItem(Base):
    __tablename__ = "event_agenda_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time: Mapped[str | None] = mapped_column(String(60), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    event: Mapped[Event] = relationship(back_populates="agenda")


class RSVP(Base):
    __tablename__ = "rsvps"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255))
    names: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[str | None] = mapped_column(String(60), nullable=True)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rsvp: Mapped[str] = mapped_column(String(30), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped[Event] = relationship(back_populates="rsvps")
