from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials. Admins and members both authenticate by email."""

    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: str
