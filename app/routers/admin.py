from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.categories import MEMBER_CATEGORIES, normalise_categories
from app.core.deps import get_current_admin
from app.core.industries import normalise_industries
from app.core.security import hash_password
from app.core.uploads import (
    MAX_UPLOAD_BYTES,
    UPLOAD_URL_PREFIX,
    build_stored_name,
    detect_extension,
    ensure_upload_dir,
)
from app.db.session import get_db
from app.models.article import Article
from app.models.connection import (
    ACCEPTED,
    DECLINED,
    PENDING,
    REPORTED,
    ConnectionReport,
    ConnectionRequest,
)
from app.models.contact import Contact
from app.models.event import RSVP, Event, EventAgendaItem, EventPhoto, EventSpeaker
from app.models.member import Member
from app.schemas.article import ArticleIn, ArticleOut
from app.schemas.connection import AdminConnectionOut, ConnectionReportOut
from app.schemas.contact import ContactOut, ContactStatusUpdate
from app.schemas.event import EventIn, EventOut, RSVPOut
from app.schemas.member import MemberActiveUpdate, MemberAdminCreateRequest, MemberOut
from app.schemas.stats import (
    CategoryCount,
    ConnectionStats,
    ConnectorStat,
    MemberActivityOut,
    MemberConnectionSummary,
    MemberEventSummary,
    MessagesBreakdown,
    RecentMember,
    StatsOut,
    TierCount,
    UpcomingEventStat,
)

router = APIRouter(dependencies=[Depends(get_current_admin)])


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------




async def _connection_stats(db: AsyncSession, window_30d, window_60d) -> ConnectionStats:
    """Everything the dashboard shows about connections, in one pass."""

    async def count_where(*conditions) -> int:
        return (
            await db.execute(select(func.count(ConnectionRequest.id)).where(*conditions))
        ).scalar_one()

    total = (await db.execute(select(func.count(ConnectionRequest.id)))).scalar_one()
    accepted = await count_where(ConnectionRequest.status == ACCEPTED)
    declined = await count_where(ConnectionRequest.status == DECLINED)
    pending = await count_where(ConnectionRequest.status == PENDING)
    reported = await count_where(ConnectionRequest.status == REPORTED)

    answered = accepted + declined + reported
    acceptance_rate = round(accepted / answered * 100, 1) if answered else None

    week_ago = datetime.now(UTC) - timedelta(days=7)
    stale_pending = await count_where(
        ConnectionRequest.status == PENDING, ConnectionRequest.created_at < week_ago
    )

    requests_30d = await count_where(ConnectionRequest.created_at >= window_30d)
    requests_prev_30d = await count_where(
        ConnectionRequest.created_at >= window_60d, ConnectionRequest.created_at < window_30d
    )
    accepted_30d = await count_where(
        ConnectionRequest.status == ACCEPTED, ConnectionRequest.responded_at >= window_30d
    )

    # Median rather than mean: a single request answered six months late would drag an
    # average into uselessness, while the median still describes the typical experience.
    response_hours = (
        func.extract("epoch", ConnectionRequest.responded_at - ConnectionRequest.created_at)
        / 3600.0
    ).label("response_hours")
    gaps = (
        await db.execute(
            select(response_hours)
            .where(ConnectionRequest.responded_at.is_not(None))
            .order_by(response_hours)
        )
    ).scalars().all()
    # Coerced to float up front: the driver hands back Decimal for this expression, and
    # Decimal + float is a TypeError, so averaging the middle pair of an even-sized list
    # would blow up on mixed types.
    hours = [float(gap) for gap in gaps]
    median_response_hours = None
    if hours:
        mid = len(hours) // 2
        median = hours[mid] if len(hours) % 2 else (hours[mid - 1] + hours[mid]) / 2
        median_response_hours = round(median, 1)

    accepted_rows = (
        await db.execute(
            select(ConnectionRequest.requester_id, ConnectionRequest.recipient_id).where(
                ConnectionRequest.status == ACCEPTED
            )
        )
    ).all()
    connected_ids: set[int] = set()
    per_member: dict[int, int] = {}
    for requester_id, recipient_id in accepted_rows:
        for member_id in (requester_id, recipient_id):
            connected_ids.add(member_id)
            per_member[member_id] = per_member.get(member_id, 0) + 1

    incoming_rows = (
        await db.execute(
            select(ConnectionRequest.recipient_id, func.count(ConnectionRequest.id)).group_by(
                ConnectionRequest.recipient_id
            )
        )
    ).all()
    incoming_counts: dict[int, int] = {row[0]: row[1] for row in incoming_rows}

    interesting_ids = set(per_member) | set(incoming_counts)
    members = (
        (await db.execute(select(Member).where(Member.id.in_(interesting_ids)))).scalars().all()
        if interesting_ids
        else []
    )
    by_id = {m.id: m for m in members}

    def leaderboard(counts: dict[int, int]) -> list[ConnectorStat]:
        top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return [
            ConnectorStat(
                id=member_id,
                name=f"{by_id[member_id].first_name} {by_id[member_id].last_name}".strip(),
                email=by_id[member_id].email,
                count=count,
            )
            for member_id, count in top
            if member_id in by_id
        ]

    directory_eligible = (
        await db.execute(
            select(func.count(Member.id)).where(
                Member.active.is_(True),
                Member.is_searchable.is_(True),
                Member.membership_tier != "Basic Membership",
            )
        )
    ).scalar_one()

    total_reports = (await db.execute(select(func.count(ConnectionReport.id)))).scalar_one()
    open_reports = (
        await db.execute(
            select(func.count(ConnectionReport.id)).where(ConnectionReport.reviewed.is_(False))
        )
    ).scalar_one()

    return ConnectionStats(
        total_requests=total,
        accepted=accepted,
        declined=declined,
        pending=pending,
        reported=reported,
        acceptance_rate=acceptance_rate,
        stale_pending=stale_pending,
        median_response_hours=median_response_hours,
        requests_30d=requests_30d,
        requests_prev_30d=requests_prev_30d,
        accepted_30d=accepted_30d,
        members_with_connections=len(connected_ids),
        directory_eligible=directory_eligible,
        most_connected=leaderboard(per_member),
        most_requested=leaderboard(incoming_counts),
        open_reports=open_reports,
        total_reports=total_reports,
    )

@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    total_members = (await db.execute(select(func.count(Member.id)))).scalar_one()
    total_articles = (await db.execute(select(func.count(Article.id)))).scalar_one()
    total_events = (await db.execute(select(func.count(Event.id)))).scalar_one()
    active_events = (
        await db.execute(select(func.count(Event.id)).where(Event.has_happened.is_(False)))
    ).scalar_one()
    new_messages = (
        await db.execute(select(func.count(Contact.id)).where(Contact.status == "new"))
    ).scalar_one()
    replied_messages = (
        await db.execute(select(func.count(Contact.id)).where(Contact.status == "replied"))
    ).scalar_one()
    closed_messages = (
        await db.execute(select(func.count(Contact.id)).where(Contact.status == "closed"))
    ).scalar_one()

    now = datetime.now(UTC)
    window_30d = now - timedelta(days=30)
    window_60d = now - timedelta(days=60)
    window_7d = now - timedelta(days=7)

    async def count_between(model, start, end=None):
        stmt = select(func.count(model.id)).where(model.created_at >= start)
        if end is not None:
            stmt = stmt.where(model.created_at < end)
        return (await db.execute(stmt)).scalar_one()

    new_members_30d = await count_between(Member, window_30d)
    new_members_prev_30d = await count_between(Member, window_60d, window_30d)
    new_members_7d = await count_between(Member, window_7d)

    active_members = (
        await db.execute(select(func.count(Member.id)).where(Member.active.is_(True)))
    ).scalar_one()
    directory_opt_in = (
        await db.execute(select(func.count(Member.id)).where(Member.is_searchable.is_(True)))
    ).scalar_one()

    tier_rows = (
        await db.execute(
            select(Member.membership_tier, func.count(Member.id))
            .group_by(Member.membership_tier)
            .order_by(func.count(Member.id).desc())
        )
    ).all()

    total_rsvps = (await db.execute(select(func.count(RSVP.id)))).scalar_one()
    rsvps_30d = await count_between(RSVP, window_30d)
    rsvps_prev_30d = await count_between(RSVP, window_60d, window_30d)

    # Upcoming events with how many people have signed up, so it's clear which need a push.
    upcoming_rows = (
        await db.execute(
            select(Event.id, Event.title, Event.date, func.count(RSVP.id))
            .outerjoin(RSVP, RSVP.event_id == Event.id)
            .where(Event.has_happened.is_(False))
            .group_by(Event.id, Event.title, Event.date)
            .order_by(Event.id.desc())
            .limit(5)
        )
    ).all()

    # Category distribution. Members are multi-category, so a single member can count
    # toward several slices - the chart shows share of members per category, not a
    # partition of the membership.
    category_rows = (
        await db.execute(select(Member.categories).where(Member.categories.isnot(None)))
    ).scalars().all()
    category_counts = {name: 0 for name in MEMBER_CATEGORIES}
    uncategorised = 0
    for row in category_rows:
        if not row:
            uncategorised += 1
            continue
        for name in row:
            if name in category_counts:
                category_counts[name] += 1

    recent_rows = (
        await db.execute(select(Member).order_by(Member.created_at.desc()).limit(5))
    ).scalars().all()

    connection_stats = await _connection_stats(db, window_30d, window_60d)

    return StatsOut(
        total_members=total_members,
        total_articles=total_articles,
        total_events=total_events,
        active_events=active_events,
        messages_breakdown=MessagesBreakdown(
            new=new_messages, replied=replied_messages, closed=closed_messages
        ),
        new_members_30d=new_members_30d,
        new_members_prev_30d=new_members_prev_30d,
        new_members_7d=new_members_7d,
        active_members=active_members,
        blocked_members=total_members - active_members,
        members_by_tier=[
            TierCount(tier=tier or "Unspecified", count=count) for tier, count in tier_rows
        ],
        total_rsvps=total_rsvps,
        rsvps_30d=rsvps_30d,
        rsvps_prev_30d=rsvps_prev_30d,
        directory_opt_in=directory_opt_in,
        upcoming_events=[
            UpcomingEventStat(id=eid, title=title, date=date, rsvp_count=count)
            for eid, title, date, count in upcoming_rows
        ],
        members_by_category=[
            CategoryCount(category=name, count=count)
            for name, count in category_counts.items()
        ],
        uncategorised_members=uncategorised,
        connections=connection_stats,
        recent_members=[
            RecentMember(
                id=m.id,
                name=f"{m.first_name} {m.last_name}".strip() or m.email,
                email=m.email,
                membership_tier=m.membership_tier,
                active=m.active,
                created_at=m.created_at,
            )
            for m in recent_rows
        ],
    )


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@router.get("/events", response_model=list[EventOut])
async def list_events_admin(db: AsyncSession = Depends(get_db)) -> list[Event]:
    result = await db.execute(
        select(Event)
        .options(
            selectinload(Event.speakers),
            selectinload(Event.agenda),
            selectinload(Event.photos),
        )
        .order_by(Event.id.desc())
    )
    return list(result.scalars().all())


async def _get_event_or_404(event_id: int, db: AsyncSession) -> Event:
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.speakers),
            selectinload(Event.agenda),
            selectinload(Event.photos),
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventIn, db: AsyncSession = Depends(get_db)) -> Event:
    data = payload.model_dump(exclude={"speakers", "agenda", "photos"})
    event = Event(**data)
    event.speakers = [EventSpeaker(**s.model_dump(exclude={"id"})) for s in payload.speakers]
    event.agenda = [
        EventAgendaItem(**a.model_dump(exclude={"id"}), order=i)
        for i, a in enumerate(payload.agenda)
    ]
    # Order comes from the list position rather than the submitted value, so rearranging
    # in the editor is all it takes to rearrange the gallery.
    event.photos = [
        EventPhoto(url=ph.url, caption=ph.caption, order=i) for i, ph in enumerate(payload.photos)
    ]
    db.add(event)
    await db.commit()
    return await _get_event_or_404(event.id, db)


@router.put("/events/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int, payload: EventIn, db: AsyncSession = Depends(get_db)
) -> Event:
    event = await _get_event_or_404(event_id, db)
    data = payload.model_dump(exclude={"speakers", "agenda", "photos"})
    for field, value in data.items():
        setattr(event, field, value)

    event.speakers = [EventSpeaker(**s.model_dump(exclude={"id"})) for s in payload.speakers]
    event.agenda = [
        EventAgendaItem(**a.model_dump(exclude={"id"}), order=i)
        for i, a in enumerate(payload.agenda)
    ]
    # Order comes from the list position rather than the submitted value, so rearranging
    # in the editor is all it takes to rearrange the gallery.
    event.photos = [
        EventPhoto(url=ph.url, caption=ph.caption, order=i) for i, ph in enumerate(payload.photos)
    ]
    await db.commit()
    return await _get_event_or_404(event_id, db)


@router.get("/events/{event_id}/rsvps", response_model=list[RSVPOut])
async def list_event_rsvps(event_id: int, db: AsyncSession = Depends(get_db)) -> list[RSVPOut]:
    await _get_event_or_404(event_id, db)
    result = await db.execute(
        select(RSVP).where(RSVP.event_id == event_id).order_by(RSVP.id.desc())
    )
    rsvps = result.scalars().all()
    return [
        RSVPOut(
            id=r.id,
            names=r.names,
            email=r.email,
            company=r.company,
            price=r.price,
            rsvp=r.rsvp,
            paymentIntentId=r.payment_intent_id,
        )
        for r in rsvps
    ]


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------


@router.get("/articles", response_model=list[ArticleOut])
async def list_articles_admin(db: AsyncSession = Depends(get_db)) -> list[Article]:
    result = await db.execute(select(Article).order_by(Article.id.desc()))
    return list(result.scalars().all())


@router.post("/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article(payload: ArticleIn, db: AsyncSession = Depends(get_db)) -> Article:
    article = Article(**payload.model_dump())
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Permanently remove an article.

    Unpublishing hides an article and is reversible, which covers most cases. This is for
    the rest: a duplicate, a draft that will never run, something posted by mistake.
    """
    article = (
        await db.execute(select(Article).where(Article.id == article_id))
    ).scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    await db.delete(article)
    await db.commit()


@router.put("/articles/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: int, payload: ArticleIn, db: AsyncSession = Depends(get_db)
) -> Article:
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    for field, value in payload.model_dump().items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    return article


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/members", response_model=list[MemberOut])
async def list_members_admin(db: AsyncSession = Depends(get_db)) -> list[Member]:
    result = await db.execute(select(Member).order_by(Member.id.desc()))
    return list(result.scalars().all())


@router.post("/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def create_member_admin(
    payload: MemberAdminCreateRequest, db: AsyncSession = Depends(get_db)
) -> Member:
    existing = await db.execute(select(Member).where(Member.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this email already exists",
        )

    data = payload.model_dump(exclude={"password"})
    data["categories"] = normalise_categories(data.get("categories"))
    data["industries"] = normalise_industries(data.get("industries"))
    member = Member(**data, password_hash=hash_password(payload.password), active=True)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@router.patch("/members/{member_id}/active", response_model=MemberOut)
async def set_member_active(
    member_id: int, payload: MemberActiveUpdate, db: AsyncSession = Depends(get_db)
) -> Member:
    """Block or unblock a member's access to the portal.

    `active=False` blocks them: the member login route rejects inactive accounts, so this
    takes effect on their next login attempt. Any token already issued stays valid until
    it expires.
    """
    result = await db.execute(select(Member).where(Member.id == member_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Stamp the date they left the network on block; clear it if they are reinstated.
    if member.active and not payload.active:
        member.blocked_at = datetime.now(UTC)
    elif payload.active:
        member.blocked_at = None

    member.active = payload.active
    await db.commit()
    await db.refresh(member)
    return member


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@router.get("/contacts", response_model=list[ContactOut])
async def list_contacts_admin(db: AsyncSession = Depends(get_db)) -> list[Contact]:
    result = await db.execute(select(Contact).order_by(Contact.id.desc()))
    return list(result.scalars().all())


@router.put("/contacts/{contact_id}/status", response_model=ContactOut)
async def update_contact_status(
    contact_id: int, payload: ContactStatusUpdate, db: AsyncSession = Depends(get_db)
) -> Contact:
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    contact.status = payload.status
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/connection-reports", response_model=list[ConnectionReportOut])
async def list_connection_reports(
    db: AsyncSession = Depends(get_db),
) -> list[ConnectionReportOut]:
    """Reported connection requests, unreviewed first.

    The count of reports against each member is included because that is the signal worth
    acting on: a single report is often a disagreement, a pattern is not.
    """
    result = await db.execute(
        select(ConnectionReport).order_by(
            ConnectionReport.reviewed.asc(), ConnectionReport.created_at.desc()
        )
    )
    reports = result.scalars().all()
    if not reports:
        return []

    count_rows = (
        await db.execute(
            select(ConnectionReport.reported_member_id, func.count(ConnectionReport.id)).group_by(
                ConnectionReport.reported_member_id
            )
        )
    ).all()
    counts: dict[int, int] = {row[0]: row[1] for row in count_rows}

    member_ids = {r.reporter_id for r in reports} | {r.reported_member_id for r in reports}
    members = (
        (await db.execute(select(Member).where(Member.id.in_(member_ids)))).scalars().all()
    )
    by_id = {m.id: m for m in members}

    def name(member_id: int) -> str:
        m = by_id.get(member_id)
        return f"{m.first_name} {m.last_name}".strip() if m else "Removed member"

    def email(member_id: int) -> str:
        m = by_id.get(member_id)
        return m.email if m else ""

    return [
        ConnectionReportOut(
            id=r.id,
            reason=r.reason,
            details=r.details,
            reported_message=r.reported_message,
            reviewed=r.reviewed,
            created_at=r.created_at,
            reporter_name=name(r.reporter_id),
            reporter_email=email(r.reporter_id),
            reported_name=name(r.reported_member_id),
            reported_email=email(r.reported_member_id),
            reported_member_id=r.reported_member_id,
            reported_member_active=bool(
                by_id[r.reported_member_id].active
            ) if r.reported_member_id in by_id else False,
            reports_against_member=counts.get(r.reported_member_id, 0),
        )
        for r in reports
    ]


@router.patch("/connection-reports/{report_id}")
async def mark_report_reviewed(
    report_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Mark a report as dealt with.

    Marking it reviewed says the team has looked; it does not act on the member. Blocking
    someone stays a separate and deliberate call, on the members endpoint.
    """
    report = (
        await db.execute(select(ConnectionReport).where(ConnectionReport.id == report_id))
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.reviewed = True
    await db.commit()
    return {"detail": "Report marked as reviewed"}


# Fields a directory listing needs to be worth reading. Used to score completeness, which
# is the quickest explanation for "why is nobody connecting with this member".
_PROFILE_FIELDS = [
    ("company", "Company"),
    ("bio", "Bio"),
    ("interests", "Interests"),
    ("phone", "Phone"),
    ("linkedin", "LinkedIn"),
    ("industries", "Sectors"),
    ("categories", "Member type"),
]


@router.get("/members/{member_id}/activity", response_model=MemberActivityOut)
async def get_member_activity(
    member_id: int, db: AsyncSession = Depends(get_db)
) -> MemberActivityOut:
    """What a member has done: events, connections and reports."""
    member = (
        await db.execute(select(Member).where(Member.id == member_id))
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Events. RSVPs are keyed by email, matched case-insensitively for the same reason the
    # member-facing endpoint does it: the public form takes a free-typed address.
    event_rows = (
        await db.execute(
            select(RSVP, Event)
            .join(Event, Event.id == RSVP.event_id)
            .where(func.lower(RSVP.email) == member.email.lower())
            .order_by(RSVP.created_at.desc())
        )
    ).all()

    seen_events: set[int] = set()
    recent_events: list[MemberEventSummary] = []
    attended = 0
    for rsvp, event in event_rows:
        if event.id in seen_events:
            continue
        seen_events.add(event.id)
        did_attend = bool(event.has_happened and rsvp.rsvp != "cancelled")
        attended += 1 if did_attend else 0
        if len(recent_events) < 5:
            recent_events.append(
                MemberEventSummary(title=event.title, date=event.date, attended=did_attend)
            )

    # Connections, both directions.
    conn_rows = (
        await db.execute(
            select(ConnectionRequest)
            .where(
                or_(
                    ConnectionRequest.requester_id == member.id,
                    ConnectionRequest.recipient_id == member.id,
                )
            )
            .order_by(ConnectionRequest.created_at.desc())
        )
    ).scalars().all()

    other_ids = {
        r.recipient_id if r.requester_id == member.id else r.requester_id for r in conn_rows
    }
    others = (
        (await db.execute(select(Member).where(Member.id.in_(other_ids)))).scalars().all()
        if other_ids
        else []
    )
    by_id = {m.id: m for m in others}

    counts = {
        "connections": 0,
        "requests_sent": 0,
        "requests_received": 0,
        "pending_incoming": 0,
        "pending_outgoing": 0,
        "declined_by_them": 0,
        "declined_by_others": 0,
    }
    recent_connections: list[MemberConnectionSummary] = []

    for r in conn_rows:
        outgoing = r.requester_id == member.id
        other = by_id.get(r.recipient_id if outgoing else r.requester_id)

        counts["requests_sent" if outgoing else "requests_received"] += 1
        if r.status == ACCEPTED:
            counts["connections"] += 1
        elif r.status == PENDING:
            counts["pending_outgoing" if outgoing else "pending_incoming"] += 1
        elif r.status == DECLINED:
            # Who did the declining, which is the difference between being turned down and
            # turning people down.
            counts["declined_by_others" if outgoing else "declined_by_them"] += 1

        # No cap: an admin looking at one member wants the whole relationship history,
        # not a sample of it. A member with hundreds of these is itself worth seeing.
        if other is not None:
            recent_connections.append(
                MemberConnectionSummary(
                    member_id=other.id,
                    name=f"{other.first_name} {other.last_name}".strip(),
                    email=other.email,
                    company=other.company,
                    status=r.status,
                    direction="outgoing" if outgoing else "incoming",
                    message=r.message,
                    created_at=r.created_at,
                    responded_at=r.responded_at,
                )
            )

    reports_against = (
        await db.execute(
            select(func.count(ConnectionReport.id)).where(
                ConnectionReport.reported_member_id == member.id
            )
        )
    ).scalar_one()
    reports_made = (
        await db.execute(
            select(func.count(ConnectionReport.id)).where(
                ConnectionReport.reporter_id == member.id
            )
        )
    ).scalar_one()

    missing = [
        label
        for field, label in _PROFILE_FIELDS
        if not getattr(member, field, None)
    ]
    completeness = round((len(_PROFILE_FIELDS) - len(missing)) / len(_PROFILE_FIELDS) * 100)

    return MemberActivityOut(
        member_id=member.id,
        events_registered=len(seen_events),
        events_attended=attended,
        recent_events=recent_events,
        recent_connections=recent_connections,
        reports_against=reports_against,
        reports_made=reports_made,
        profile_completeness=completeness,
        missing_fields=missing,
        **counts,
    )


@router.get("/connections", response_model=list[AdminConnectionOut])
async def list_all_connections(db: AsyncSession = Depends(get_db)) -> list[AdminConnectionOut]:
    """Every connection request on the site, newest first.

    Both parties are resolved here rather than returning ids, because the only useful view
    of a connection is "who asked whom", and making the client join that itself would mean
    shipping the whole member list to the browser.
    """
    requests = (
        await db.execute(
            select(ConnectionRequest).order_by(ConnectionRequest.created_at.desc())
        )
    ).scalars().all()
    if not requests:
        return []

    member_ids = {r.requester_id for r in requests} | {r.recipient_id for r in requests}
    members = (
        (await db.execute(select(Member).where(Member.id.in_(member_ids)))).scalars().all()
    )
    by_id = {m.id: m for m in members}

    reported_ids = {
        row[0]
        for row in (
            await db.execute(select(ConnectionReport.request_id).distinct())
        ).all()
    }

    def name(member_id: int) -> str:
        m = by_id.get(member_id)
        return f"{m.first_name} {m.last_name}".strip() if m else "Removed member"

    def email(member_id: int) -> str:
        m = by_id.get(member_id)
        return m.email if m else ""

    def company(member_id: int) -> str | None:
        m = by_id.get(member_id)
        return m.company if m else None

    return [
        AdminConnectionOut(
            id=r.id,
            status=r.status,
            message=r.message,
            created_at=r.created_at,
            responded_at=r.responded_at,
            requester_id=r.requester_id,
            requester_name=name(r.requester_id),
            requester_email=email(r.requester_id),
            requester_company=company(r.requester_id),
            recipient_id=r.recipient_id,
            recipient_name=name(r.recipient_id),
            recipient_email=email(r.recipient_id),
            recipient_company=company(r.recipient_id),
            reported=r.id in reported_ids,
        )
        for r in requests
    ]


@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    """Store an uploaded image and return the URL to reference it by.

    Admin-only, via the router's dependency. The response is the public path, which is what
    goes straight into an article's markup.
    """
    head = await file.read(32)
    extension = detect_extension(head)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file is not a JPEG, PNG, GIF or WebP image.",
        )

    directory = ensure_upload_dir()
    stored_name = build_stored_name(extension)
    destination = directory / stored_name

    written = len(head)
    try:
        with destination.open("wb") as out:
            out.write(head)
            # Streamed in chunks and checked as it goes, so an oversized file is rejected
            # before it has all been written rather than after.
            while chunk := await file.read(1024 * 256):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    out.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Images must be under {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save the image."
        ) from exc

    return {"url": f"{UPLOAD_URL_PREFIX}/{stored_name}", "filename": stored_name}
