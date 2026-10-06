import stripe
from fastapi import HTTPException, status

from app.core.config import settings

stripe.api_key = settings.stripe_secret_key or None


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def require_client_secret(intent: stripe.PaymentIntent) -> str:
    """The intent's client secret, or a 502 if Stripe did not return one.

    Typed as optional in the Stripe SDK, and the frontend cannot confirm a payment
    without it. Handing the None straight to the response model would surface as an
    opaque 500 from a serialisation failure, which tells nobody anything.
    """
    secret = intent.client_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider did not return a usable payment secret.",
        )
    return secret
