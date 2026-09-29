"""Authentication: password hashing + JWT issue/verify + current-user dependency."""
from __future__ import annotations

import datetime as dt

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Subscription, Tier, User

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
ALGORITHM = "HS256"

# bcrypt operates on bytes and only uses the first 72 bytes of the password.
_BCRYPT_MAX_BYTES = 72


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a password with bcrypt. Returns the encoded hash as a str.

    Uses the `bcrypt` library directly (passlib was dropped due to its
    incompatibility with bcrypt >= 4.1 — the 'no attribute __about__' error)."""
    hashed = bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exc
    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


def is_paid(user: User | None) -> bool:
    if user is None or user.subscription is None:
        return False
    return user.subscription.tier == Tier.paid.value and user.subscription.active


def require_paid(user: User = Depends(get_current_user)) -> User:
    if not is_paid(user):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This feature requires a Candorify paid subscription.",
        )
    return user
