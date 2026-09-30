import argparse
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.seed import seed_initial_data, seed_members
from app.db.session import SessionLocal
from app.models.admin_user import AdminUser
from app.models.member import Member


async def create_admin(email: str, password: str, reset: bool = False) -> None:
    """Create an admin. Pass reset=True to overwrite the password of an existing one."""
    async with SessionLocal() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.email == email))
        admin = result.scalar_one_or_none()
        if admin is not None:
            if not reset:
                print(f"Admin '{email}' already exists. Pass --reset to set a new password.")
                return
            admin.password_hash = hash_password(password)
            await db.commit()
            print(f"Reset password for admin '{email}'.")
            return
        db.add(AdminUser(email=email, password_hash=hash_password(password)))
        await db.commit()
        print(f"Created admin '{email}'.")


async def create_member(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    tier: str = "Basic Membership",
) -> None:
    """Create a member that can log in straight away.

    Public applications land with active=False pending admin review, so this sets
    active=True to make the account immediately usable.
    """
    async with SessionLocal() as db:
        result = await db.execute(select(Member).where(Member.email == email))
        member = result.scalar_one_or_none()
        if member is not None:
            member.password_hash = hash_password(password)
            member.active = True
            member.membership_tier = tier
            await db.commit()
            print(f"Member '{email}' already existed - password reset and account activated.")
            return
        db.add(
            Member(
                email=email,
                password_hash=hash_password(password),
                first_name=first_name,
                last_name=last_name,
                membership_tier=tier,
                active=True,
            )
        )
        await db.commit()
        print(f"Created member '{email}'.")


async def seed() -> None:
    async with SessionLocal() as db:
        await seed_initial_data(db)


async def seed_people(password: str) -> None:
    async with SessionLocal() as db:
        await seed_members(db, password)


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser("create-admin")
    create_admin_parser.add_argument("--email", required=True)
    create_admin_parser.add_argument("--password", required=True)
    create_admin_parser.add_argument(
        "--reset",
        action="store_true",
        help="overwrite the password if the admin already exists",
    )

    create_member_parser = subparsers.add_parser("create-member")
    create_member_parser.add_argument("--email", required=True)
    create_member_parser.add_argument("--password", required=True)
    create_member_parser.add_argument("--first-name", default="Test")
    create_member_parser.add_argument("--last-name", default="Member")
    create_member_parser.add_argument("--tier", default="Basic Membership")

    subparsers.add_parser("seed")

    seed_members_parser = subparsers.add_parser(
        "seed-members", help="populate the database with 30 demo members (development only)"
    )
    seed_members_parser.add_argument(
        "--password",
        default="sgnmember123",
        help="shared login password for every seeded member",
    )

    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(create_admin(args.email, args.password, args.reset))
    elif args.command == "create-member":
        asyncio.run(
            create_member(
                args.email, args.password, args.first_name, args.last_name, args.tier
            )
        )
    elif args.command == "seed":
        asyncio.run(seed())
    elif args.command == "seed-members":
        asyncio.run(seed_people(args.password))


if __name__ == "__main__":
    main()
