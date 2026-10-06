import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.categories import normalise_categories
from app.core.industries import normalise_industries
from app.core.membership_tiers import MEMBERSHIP_TIER_PRICES_GBP
from app.core.stripe_client import is_configured
from app.db.session import get_db
from app.models.article import Article
from app.models.contact import Contact
from app.models.event import RSVP, Event
from app.models.member import Member
from app.schemas.article import ArticleOut
from app.schemas.contact import ContactIn, ContactOut
from app.schemas.event import (
    EventOut,
    PaymentIntentEventRequest,
    PaymentIntentResponse,
    RSVPRequest,
)
from app.schemas.member import MemberApplicationRequest, MemberOut
from app.schemas.payment import MembershipPaymentIntentRequest

router = APIRouter()


@router.get("/events", response_model=list[EventOut])
async def list_events(db: AsyncSession = Depends(get_db)) -> list[Event]:
    result = await db.execute(
        select(Event)
        .where(Event.published.is_(True))
        .options(
            selectinload(Event.speakers),
            selectinload(Event.agenda),
            selectinload(Event.photos),
        )
        .order_by(Event.id.desc())
    )
    return list(result.scalars().all())


@router.get("/articles", response_model=list[ArticleOut])
async def list_articles(db: AsyncSession = Depends(get_db)) -> list[Article]:
    result = await db.execute(
        select(Article).where(Article.published.is_(True)).order_by(Article.id.desc())
    )
    return list(result.scalars().all())


@router.get("/events/{event_id}", response_model=EventOut)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> Event:
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


@router.post("/rsvp", status_code=status.HTTP_201_CREATED)
async def create_rsvp(payload: RSVPRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    result = await db.execute(select(Event).where(Event.id == payload.event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    rsvp = RSVP(
        event_id=payload.event_id,
        email=payload.email,
        names=payload.names,
        company=payload.company,
        price=payload.price,
        payment_intent_id=payload.paymentIntentId or None,
        rsvp="confirmed",
    )
    db.add(rsvp)
    await db.commit()
    return {"detail": "RSVP recorded"}


@router.post("/contact", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def submit_contact(payload: ContactIn, db: AsyncSession = Depends(get_db)) -> Contact:
    contact = Contact(**payload.model_dump(), status="new")
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.post("/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def apply_for_membership(
    payload: MemberApplicationRequest, db: AsyncSession = Depends(get_db)
) -> Member:
    existing = await db.execute(select(Member).where(Member.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this email already exists",
        )

    member = Member(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        company=payload.company,
        industry=payload.industry,
        # Normalised against the canonical lists so the columns stay trustworthy, the same
        # way the profile update endpoint treats them.
        industries=normalise_industries(payload.industries),
        categories=normalise_categories(payload.categories),
        interests=payload.interests,
        phone=payload.phone,
        membership_tier=payload.membershipTier,
        payment_intent_id=payload.paymentIntentId or None,
        active=False,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_membership_payment_intent(
    payload: MembershipPaymentIntentRequest,
) -> PaymentIntentResponse:
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured on this server yet.",
        )
    if payload.membershipTier not in MEMBERSHIP_TIER_PRICES_GBP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown membership tier",
        )

    real_amount_pence = round(MEMBERSHIP_TIER_PRICES_GBP[payload.membershipTier] * 100)
    if real_amount_pence <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This tier does not require payment",
        )

    intent = stripe.PaymentIntent.create(
        amount=real_amount_pence,
        currency="gbp",
        metadata={"membershipTier": payload.membershipTier},
    )
    return PaymentIntentResponse(clientSecret=intent.client_secret)


@router.post("/create-payment-intent-event", response_model=PaymentIntentResponse)
async def create_event_payment_intent(
    payload: PaymentIntentEventRequest, db: AsyncSession = Depends(get_db)
) -> PaymentIntentResponse:
    if not is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured on this server yet.",
        )
    result = await db.execute(select(Event).where(Event.id == payload.eventId))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    try:
        real_amount_pence = round(float(str(event.price).replace("£", "").strip()) * 100)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This event is not paid"
        ) from exc
    if real_amount_pence <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This event does not require payment"
        )

    intent = stripe.PaymentIntent.create(
        amount=real_amount_pence,
        currency="gbp",
        metadata={"eventId": str(payload.eventId)},
    )
    return PaymentIntentResponse(clientSecret=intent.client_secret)
