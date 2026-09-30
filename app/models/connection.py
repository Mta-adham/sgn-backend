from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.member import Member

# The states a request can be in. Declined requests are kept rather than deleted: without
# them a rejected member could send the same request again immediately, and the recipient
# would have no way to stop it.
PENDING = "pending"
ACCEPTED = "accepted"
DECLINED = "declined"
WITHDRAWN = "withdrawn"

# A request the recipient reported. Kept distinct from "declined" so the admin queue and
# the member's own list can tell a refusal from an abuse report.
REPORTED = "reported"

CONNECTION_STATUSES = (PENDING, ACCEPTED, DECLINED, WITHDRAWN, REPORTED)


class ConnectionRequest(Base):
    """One member asking to be introduced to another.

    Contact details are only exchanged once the recipient accepts. Until then the requester
    learns nothing they could not already see in the directory, so a request cannot be used
    to harvest addresses.
    """

    __tablename__ = "connection_requests"
    __table_args__ = (
        # At most one live request per direction. Enforced in the database rather than only
        # in the endpoint, so a double-clicked button or a retried call cannot create two.
        UniqueConstraint("requester_id", "recipient_id", name="uq_connection_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True
    )
    # Why they want to connect. Optional, but it is what lets the recipient make an informed
    # decision rather than guessing.
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requester: Mapped[Member] = relationship(foreign_keys=[requester_id])
    recipient: Mapped[Member] = relationship(foreign_keys=[recipient_id])


class ConnectionReport(Base):
    """A member reporting a connection request they received.

    Reports are rows rather than a flag on the request so that the reason, the reporter and
    the time survive independently: the request may later be declined, reopened or deleted,
    and the record of the report should not go with it.
    """

    __tablename__ = "connection_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("connection_requests.id", ondelete="CASCADE"), index=True
    )
    # Denormalised so a report still names the people involved after the request is gone.
    reporter_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    reported_member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(40))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A copy of what was actually sent. The request can be edited or removed; what the
    # reporter saw is the thing being judged, so it is stored here.
    reported_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


REPORT_REASONS = (
    "contact_details",
    "inappropriate",
    "spam",
    "impersonation",
    "other",
)
