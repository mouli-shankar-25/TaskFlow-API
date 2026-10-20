import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


async def register_user(db: AsyncSession, name: str, email: str, password: str) -> User:
    """Register a new user. Raises ConflictError if email exists."""
    email = email.strip().lower()
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("A user with this email already exists")

    user = User(
        name=name.strip(),
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> tuple[User, str]:
    """Authenticate and return (user, access_token). Raises UnauthorizedError."""
    email = email.strip().lower()
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Constant-time-ish: don't reveal whether email exists
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    token = create_access_token(subject=str(user.id))
    return user, token


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Fetch a user by their unique UUID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user by their email address."""
    email = email.strip().lower()
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_user_profile(db: AsyncSession, user: User, name: str | None = None) -> User:
    """Update profile fields. Only name is updatable by the user."""
    if name is not None:
        user.name = name.strip()
    db.add(user)
    await db.flush()
    return user
