from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.categories import MEMBER_CATEGORIES
from app.core.industries import INDUSTRIES
from app.core.membership_tiers import MEMBERSHIP_TIER_PRICES_GBP
from app.core.security import hash_password
from app.db.seed_data import SEED_ARTICLES, SEED_EVENTS
from app.db.seed_members_data import SEED_MEMBERS
from app.models.article import Article
from app.models.event import Event, EventAgendaItem, EventSpeaker
from app.models.member import Member


async def seed_initial_data(db: AsyncSession, force: bool = False) -> None:
    """Load the starter events and articles into an *empty* database.

    Only ever populates empty tables. Matching on title is not enough to make this safe
    to re-run: once content has been edited through the admin panel - a title corrected,
    an event renamed, an article rewritten - the seed row no longer matches, and a second
    run silently inserts the stale original alongside the edited one. The table being
    non-empty is the real signal that this data is now the admin's to manage, not ours.

    Pass force=True to seed regardless, which is only sensible when you have just
    deliberately emptied the tables.
    """
    event_count = (await db.execute(select(func.count(Event.id)))).scalar_one()
    article_count = (await db.execute(select(func.count(Article.id)))).scalar_one()

    if not force and (event_count or article_count):
        print(
            f"Database already has {event_count} event(s) and {article_count} article(s); "
            "leaving them alone.\n"
            "This content is managed through the admin panel once it exists. Re-seeding "
            "would duplicate anything whose title has since been edited.\n"
            "Pass --force if you have deliberately emptied the tables and want the "
            "starter content back."
        )
        return

    for event_data in SEED_EVENTS:
        existing = await db.execute(select(Event).where(Event.title == event_data["title"]))
        if existing.scalar_one_or_none() is not None:
            print(f"Event '{event_data['title']}' already exists, skipping.")
            continue

        data: dict[str, Any] = dict(event_data)
        speakers: list[dict[str, Any]] = data.pop("speakers", [])
        agenda: list[dict[str, Any]] = data.pop("agenda", [])
        event = Event(**data)
        event.speakers = [EventSpeaker(**speaker) for speaker in speakers]
        event.agenda = [
            EventAgendaItem(**item, order=order) for order, item in enumerate(agenda)
        ]
        db.add(event)
        print(f"Seeded event '{event_data['title']}'.")

    for article_data in SEED_ARTICLES:
        existing = await db.execute(select(Article).where(Article.title == article_data["title"]))
        if existing.scalar_one_or_none() is not None:
            print(f"Article '{article_data['title']}' already exists, skipping.")
            continue

        article: dict[str, Any] = dict(article_data)
        created_at = str(article["created_at"])
        article["created_at"] = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        db.add(Article(**article))
        print(f"Seeded article '{article_data['title']}'.")

    await db.commit()


def _validate_member(data: dict) -> None:
    """Fail loudly on an unrecognised industry, category or tier.

    normalise_industries/normalise_categories silently drop anything they don't
    recognise, which would turn a typo in the seed data into a member quietly
    missing a field. Seed data is ours to get right, so check it instead.
    """
    unknown_industries = set(data.get("industries", [])) - set(INDUSTRIES)
    if unknown_industries:
        raise ValueError(f"{data['email']}: unknown industries {sorted(unknown_industries)}")

    unknown_categories = set(data.get("categories", [])) - set(MEMBER_CATEGORIES)
    if unknown_categories:
        raise ValueError(f"{data['email']}: unknown categories {sorted(unknown_categories)}")

    tier = data.get("membership_tier")
    if tier not in MEMBERSHIP_TIER_PRICES_GBP:
        raise ValueError(f"{data['email']}: unknown membership tier {tier!r}")


async def seed_members(db: AsyncSession, password: str) -> None:
    """Insert the demo member records. Existing emails are left untouched."""
    for member_data in SEED_MEMBERS:
        _validate_member(member_data)

    created = 0
    for member_data in SEED_MEMBERS:
        email = member_data["email"]
        existing = await db.execute(select(Member).where(Member.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Member '{email}' already exists, skipping.")
            continue

        db.add(Member(**member_data, password_hash=hash_password(password)))
        created += 1
        print(f"Seeded member '{email}'.")

    await db.commit()
    if created:
        print(f"\nCreated {created} members. They all log in with password: {password}")
