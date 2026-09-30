from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.admin_user import AdminUser
from app.models.member import Member
from app.schemas.auth import ForgotPasswordRequest, LoginRequest, TokenResponse

router = APIRouter()


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(AdminUser).where(AdminUser.email == payload.email))
    admin = result.scalar_one_or_none()
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(subject=admin.email, role="admin")
    return TokenResponse(access_token=token)


@router.post("/members/login", response_model=TokenResponse)
async def member_login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(Member).where(Member.email == payload.email))
    member = result.scalar_one_or_none()
    if (
        member is None
        or member.password_hash is None
        or not verify_password(payload.password, member.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not member.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your membership application is still under review",
        )
    token = create_access_token(subject=member.email, role="member")
    return TokenResponse(access_token=token)


@router.post("/members/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    result = await db.execute(select(Member).where(Member.email == payload.email))
    member = result.scalar_one_or_none()
    # Always return success regardless of whether the email exists, so this endpoint
    # can't be used to enumerate registered members.
    if member is not None:
        # TODO: send a real reset email once an SMTP/email provider is configured.
        pass
    return {"detail": "If that email is registered, reset instructions have been sent."}
