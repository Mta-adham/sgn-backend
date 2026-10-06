from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.categories import MEMBER_CATEGORIES, normalise_categories
from app.core.deps import get_current_member
from app.core.industries import INDUSTRY_DEFINITIONS, normalise_industries
from app.core.message_filter import check_message
from app.db.session import get_db
from app.models.connection import (
    ACCEPTED,
    DECLINED,
    PENDING,
    REPORT_REASONS,
    REPORTED,
    ConnectionReport,
    ConnectionRequest,
)
from app.models.event import RSVP, Event
from app.models.member import Member
from app.schemas.connection import (
    ConnectionMemberOut,
    ConnectionOut,
    ConnectionReportCreate,
    ConnectionRequestCreate,
    ConnectionRespond,
)
from app.schemas.event import MemberEventOut
from app.schemas.member import (
    DirectoryMemberOut,
    IndustryOut,
    MemberOut,
    MemberProfileUpdateRequest,
)

router = APIRouter()

# Tiers at this index or above (0-based, matching the frontend's membershipTiers array order)
# get directory access. Index 1 = "Premium Membership".
DIRECTORY_TIER_ORDER = [
    "Basic Membership",
    "Premium Membership",
    "Corporate Membership",
    "SGN Circle",
]
DIRECTORY_MIN_TIER_INDEX = 1


def _has_directory_access(tier: str) -> bool:
    try:
        return DIRECTORY_TIER_ORDER.index(tier) >= DIRECTORY_MIN_TIER_INDEX
    except ValueError:
        return False


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """The categories a member can pick from, so the UI never hardcodes them."""
    return MEMBER_CATEGORIES


@router.get("/industries", response_model=list[IndustryOut])
async def list_industries() -> list[dict]:
    """Industries a member can pick from, with sector group and Vision 2030 flag."""
    return INDUSTRY_DEFINITIONS


@router.get("/profile", response_model=MemberOut)
async def get_profile(current_member: Member = Depends(get_current_member)) -> Member:
    return current_member


@router.put("/profile", response_model=MemberOut)
async def update_profile(
    payload: MemberProfileUpdateRequest,
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> Member:
    updates = payload.model_dump(exclude_unset=True)
    if "industries" in updates:
        updates["industries"] = normalise_industries(updates["industries"])
    if "categories" in updates:
        # Drop anything not in the canonical list so the column can be trusted downstream.
        updates["categories"] = normalise_categories(updates["categories"])
    for field, value in updates.items():
        setattr(current_member, field, value)
    await db.commit()
    await db.refresh(current_member)
    return current_member


@router.get("/directory", response_model=list[DirectoryMemberOut])
async def get_directory(
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> list[Member]:
    # Reciprocal, tier-gated visibility, enforced server-side:
    # you only see the directory if your own tier grants access AND you've opted in yourself.
    if (
        not _has_directory_access(current_member.membership_tier)
        or not current_member.is_searchable
    ):
        return []

    result = await db.execute(
        select(Member).where(
            Member.is_searchable.is_(True),
            Member.active.is_(True),
            Member.id != current_member.id,
        )
    )
    members = [m for m in result.scalars().all() if _has_directory_access(m.membership_tier)]
    return members


@router.get("/events", response_model=list[MemberEventOut])
async def get_my_events(
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> list[MemberEventOut]:
    """Events the current member has registered for, and which of those they attended.

    RSVPs are keyed by email rather than member_id, because the public RSVP form is open
    to non-members. That means the match has to be case-insensitive: the form takes a
    free-typed address, so "Ada@example.com" there and "ada@example.com" on the account
    are the same person and must not produce a half-empty history.

    Attendance is derived from the event rather than stored per RSVP. There is no
    check-in step anywhere in the product, so the only honest statement available is
    "you registered and the event has since taken place". If check-in is added later,
    this is the single place that needs to change.
    """
    result = await db.execute(
        select(RSVP, Event)
        .join(Event, Event.id == RSVP.event_id)
        .where(func.lower(RSVP.email) == current_member.email.lower())
        .order_by(RSVP.created_at.desc())
    )

    seen: set[int] = set()
    events: list[MemberEventOut] = []
    for rsvp, event in result.all():
        # A member can end up with more than one RSVP row for an event (registering
        # again, or a payment retry). Newest wins, so the list stays one row per event.
        if event.id in seen:
            continue
        seen.add(event.id)
        events.append(
            MemberEventOut(
                event_id=event.id,
                title=event.title,
                date=event.date,
                time=event.time,
                location=event.location,
                event_type=event.event_type,
                image_url=event.image_url,
                has_happened=event.has_happened,
                rsvp=rsvp.rsvp,
                registered_at=rsvp.created_at,
                attended=event.has_happened and rsvp.rsvp != "cancelled",
            )
        )
    return events


# --------------------------------------------------------------------------------------
# Connections
#
# A member asks to be introduced to another; the recipient decides. Every rule below is
# enforced here rather than in the UI, because the UI is not a security boundary.
# --------------------------------------------------------------------------------------


def _can_use_directory(member: Member) -> bool:
    """Same gate as the directory itself: right tier, and opted in.

    Connections are built on the directory, so someone who cannot be seen cannot reach
    into it either. Without this a member could opt out, stay invisible, and still send
    requests to everyone, which is exactly the asymmetry opting out is meant to prevent.
    """
    return _has_directory_access(member.membership_tier) and member.is_searchable


def _visible_member_or_404(member: Member | None) -> Member:
    """A member the viewer is allowed to act on.

    404 rather than 403 on purpose: telling someone "that member exists but is hidden from
    you" is itself a disclosure, and lets an id be probed to enumerate the membership.
    """
    if (
        member is None
        or not member.active
        or not member.is_searchable
        or not _has_directory_access(member.membership_tier)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return member


def _to_out(request: ConnectionRequest, viewer: Member) -> ConnectionOut:
    incoming = request.recipient_id == viewer.id
    other = request.requester if incoming else request.recipient
    connected = request.status == ACCEPTED

    return ConnectionOut(
        id=request.id,
        status=request.status,
        message=request.message,
        created_at=request.created_at,
        responded_at=request.responded_at,
        direction="incoming" if incoming else "outgoing",
        member=ConnectionMemberOut(
            id=other.id,
            first_name=other.first_name,
            last_name=other.last_name,
            company=other.company,
            industries=other.industries or [],
            categories=other.categories or [],
            interests=other.interests,
            # The whole point of accepting: contact details are exchanged, and only then.
            email=other.email if connected else None,
            phone=other.phone if connected else None,
            linkedin=other.linkedin if connected else None,
        ),
    )


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> list[ConnectionOut]:
    """Every request this member sent or received, newest first."""
    result = await db.execute(
        select(ConnectionRequest)
        .where(
            or_(
                ConnectionRequest.requester_id == current_member.id,
                ConnectionRequest.recipient_id == current_member.id,
            )
        )
        .order_by(ConnectionRequest.created_at.desc())
    )
    requests = result.scalars().all()

    # Load both sides in one query rather than lazily per row, which would be a round trip
    # each and fails outright under async SQLAlchemy.
    member_ids = {r.requester_id for r in requests} | {r.recipient_id for r in requests}
    if not member_ids:
        return []
    members = (
        (await db.execute(select(Member).where(Member.id.in_(member_ids)))).scalars().all()
    )
    by_id = {m.id: m for m in members}
    for r in requests:
        r.requester = by_id[r.requester_id]
        r.recipient = by_id[r.recipient_id]

    return [_to_out(r, current_member) for r in requests]


@router.post(
    "/connections", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED
)
async def request_connection(
    payload: ConnectionRequestCreate,
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ConnectionOut:
    if not _can_use_directory(current_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Connecting with members is available once you join the directory.",
        )

    if payload.recipient_id == current_member.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot connect with yourself"
        )

    recipient = (
        await db.execute(select(Member).where(Member.id == payload.recipient_id))
    ).scalar_one_or_none()
    recipient = _visible_member_or_404(recipient)

    # Either direction counts: if they already asked you, answer that rather than opening a
    # second request pointing the other way.
    existing = (
        await db.execute(
            select(ConnectionRequest).where(
                or_(
                    (ConnectionRequest.requester_id == current_member.id)
                    & (ConnectionRequest.recipient_id == recipient.id),
                    (ConnectionRequest.requester_id == recipient.id)
                    & (ConnectionRequest.recipient_id == current_member.id),
                )
            )
        )
    ).scalars().first()

    if existing is not None:
        if existing.status == ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="You are already connected"
            )
        if existing.status == PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="There is already a pending request between you",
            )
        if existing.status == DECLINED and existing.recipient_id == current_member.id:
            # They asked, you declined. Nothing stops you asking them later.
            problems = check_message(payload.message)
            if problems:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=" ".join(problems)
                )
            existing.status = PENDING
            existing.requester_id, existing.recipient_id = current_member.id, recipient.id
            existing.message = (payload.message or "").strip() or None
            existing.responded_at = None
            await db.commit()
            await db.refresh(existing)
            existing.requester, existing.recipient = current_member, recipient
            return _to_out(existing, current_member)
        # You asked and were declined. Asking again is the recipient's decision to reopen,
        # not the sender's to repeat.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This member has already responded to your request",
        )

    # Checked here, not only in the browser. A note containing an email address would
    # route around the accept step entirely, which is the one control this feature has.
    problems = check_message(payload.message)
    if problems:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=" ".join(problems))

    request = ConnectionRequest(
        requester_id=current_member.id,
        recipient_id=recipient.id,
        message=(payload.message or "").strip() or None,
        status=PENDING,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    request.requester, request.recipient = current_member, recipient
    return _to_out(request, current_member)


@router.patch("/connections/{request_id}", response_model=ConnectionOut)
async def respond_to_connection(
    request_id: int,
    payload: ConnectionRespond,
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> ConnectionOut:
    """Accept or decline. Only the recipient of a still-pending request may do this."""
    request = (
        await db.execute(select(ConnectionRequest).where(ConnectionRequest.id == request_id))
    ).scalar_one_or_none()

    # 404 rather than 403 for someone else's request: the id should not confirm anything.
    if request is None or request.recipient_id != current_member.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if request.status != PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This request has already been answered"
        )

    request.status = ACCEPTED if payload.accept else DECLINED
    request.responded_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(request)

    other = (
        await db.execute(select(Member).where(Member.id == request.requester_id))
    ).scalar_one()
    request.requester, request.recipient = other, current_member
    return _to_out(request, current_member)


@router.post("/connections/{request_id}/report", status_code=status.HTTP_201_CREATED)
async def report_connection(
    request_id: int,
    payload: ConnectionReportCreate,
    current_member: Member = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Report a request you received.

    Reporting also closes the request, so the member never has to see it again in order to
    deal with it. Nothing is hidden from the sender beyond the request being answered:
    telling them they were reported would expose whoever reported them.
    """
    if payload.reason not in REPORT_REASONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown reason")

    request = (
        await db.execute(select(ConnectionRequest).where(ConnectionRequest.id == request_id))
    ).scalar_one_or_none()

    # Only the recipient can report, and 404 rather than 403 so an id reveals nothing.
    if request is None or request.recipient_id != current_member.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    already = (
        await db.execute(
            select(ConnectionReport).where(
                ConnectionReport.request_id == request.id,
                ConnectionReport.reporter_id == current_member.id,
            )
        )
    ).scalars().first()
    if already is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You have already reported this request"
        )

    db.add(
        ConnectionReport(
            request_id=request.id,
            reporter_id=current_member.id,
            reported_member_id=request.requester_id,
            reason=payload.reason,
            details=(payload.details or "").strip() or None,
            reported_message=request.message,
        )
    )
    request.status = REPORTED
    request.responded_at = datetime.now(UTC)
    await db.commit()
    return {"detail": "Report received. The SGN team will review it."}
