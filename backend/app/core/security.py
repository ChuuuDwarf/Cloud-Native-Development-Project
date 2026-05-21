"""Password hashing + JWT encode/decode.

Uses ``bcrypt`` directly rather than ``passlib`` — passlib 1.7.4 (the latest
release, 2020) is incompatible with bcrypt 4.x (which removed ``__about__`` and
became strict about the 72-byte limit). bcrypt itself is well-maintained.
"""

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
        minutes=expires_minutes or settings.jwt_expires_minutes,
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raise JWTError on invalid/expired token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


__all__ = [
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
