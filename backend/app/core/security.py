"""Password hashing + JWT encode/decode.

Uses ``bcrypt`` directly rather than ``passlib`` — passlib 1.7.4 (the latest
release, 2020) is incompatible with bcrypt 4.x (which removed ``__about__`` and
became strict about the 72-byte limit). bcrypt itself is well-maintained.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt only consumes the first 72 bytes of the password. Truncate explicitly
# to avoid a ValueError on long inputs; Pydantic schemas should still cap
# password length (currently 72 chars) but this is defense in depth — Unicode
# passwords can exceed the byte budget at fewer chars.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str,
    *,
    extra: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.jwt_access_expires_minutes,
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise JWTError on invalid/expired token.
    Name kept for backward compat — both access and refresh tokens are
    decoded with this helper; the ``type`` claim in payload distinguishes
    hem. Callers are responsible for checking the type matches the slot
    the token came from.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def create_refresh_token(subject: str, *, expire_days: int | None = None) -> str:
    """Long-lived token used only to mint new access tokens at
    ``POST /api/auth/refresh``. Carries no display claims — the refresh
    endpoint re-reads the user from DB anyway, so embedding stale data
    here would just give attackers more leverage if the token leaks.
    """
    expire = datetime.now(UTC) + timedelta(
        days=expire_days or settings.jwt_refresh_expires_days,
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


__all__ = [
    "JWTError",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
