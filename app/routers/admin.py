from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.categories import MEMBER_CATEGORIES, normalise_categories
from app.core.deps import get_current_admin
from app.core.industries import normalise_industries
from app.core.security import hash_password
from app.db.session import get_db
from app.models.article import Article
from app.models.contact import Contact
from app.models.connection import ACCEPTED, DECLINED, PENDING, REPORTED, ConnectionReport, ConnectionRequest
from app.models.event import Event, EventAgendaItem, EventSpeaker, RSVP
from app.models.member import Member
from app.schemas.article import ArticleIn, ArticleOut
from app.schemas.contact import ContactOut, ContactStatusUpdate
from app.schemas.connection import ConnectionReportOut
from app.schemas.stats import ConnectionStats, ConnectorStat
from app.schemas.event import EventIn, EventOut, RSVPOut
from app.schemas.member import MemberActiveUpdate, MemberAdminCreateRequest, MemberOut
from app.schemas.stats import (
    CategoryCount,
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

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
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
    median_response_hours = None
    if gaps:
        mid = len(gaps) // 2
        median_response_hours = round(
            float(gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2), 1
        )

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

    incoming_counts = dict(
        (
            await db.execute(
                select(ConnectionRequest.recipient_id, func.count(ConnectionRequest.id))
                .group_by(ConnectionRequest.recipient_id)
            )
        ).all()
    )

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

    now = datetime.now(timezone.utc)
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
        .options(selectinload(Event.speakers), selectinload(Event.agenda))
        .order_by(Event.id.desc())
    )
    return list(result.scalars().all())


async def _get_event_or_404(event_id: int, db: AsyncSession) -> Event:
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.speakers), selectinload(Event.agenda))
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventIn, db: AsyncSession = Depends(get_db)) -> Event:
    data = payload.model_dump(exclude={"speakers", "agenda"})
    event = Event(**data)
    event.speakers = [EventSpeaker(**s.model_dump(exclude={"id"})) for s in payload.speakers]
    event.agenda = [
        EventAgendaItem(**a.model_dump(exclude={"id"}), order=i) for i, a in enumerate(payload.agenda)
    ]
    db.add(event)
    await db.commit()
    return await _get_event_or_404(event.id, db)


@router.put("/events/{event_id}", response_model=EventOut)
async def update_event(event_id: int, payload: EventIn, db: AsyncSession = Depends(get_db)) -> Event:
    event = await _get_event_or_404(event_id, db)
    data = payload.model_dump(exclude={"speakers", "agenda"})
    for field, value in data.items():
        setattr(event, field, value)

    event.speakers = [EventSpeaker(**s.model_dump(exclude={"id"})) for s in payload.speakers]
    event.agenda = [
        EventAgendaItem(**a.model_dump(exclude={"id"}), order=i) for i, a in enumerate(payload.agenda)
    ]
    await db.commit()
    return await _get_event_or_404(event_id, db)


@router.get("/events/{event_id}/rsvps", response_model=list[RSVPOut])
async def list_event_rsvps(event_id: int, db: AsyncSession = Depends(get_db)) -> list[RSVPOut]:
    await _get_event_or_404(event_id, db)
    result = await db.execute(select(RSVP).where(RSVP.event_id == event_id).order_by(RSVP.id.desc()))
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A member with this email already exists")

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
        member.blocked_at = datetime.now(timezone.utc)
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

    counts = dict(
        (
            await db.execute(
                select(ConnectionReport.reported_member_id, func.count(ConnectionReport.id))
                .group_by(ConnectionReport.reported_member_id)
            )
        ).all()
    )

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
