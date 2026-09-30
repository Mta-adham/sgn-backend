from pydantic import BaseModel


class MembershipPaymentIntentRequest(BaseModel):
    amount: float
    membershipTier: str
    memberDetails: dict = {}
